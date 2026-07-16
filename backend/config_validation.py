from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse


PLACEHOLDER_VALUES = {
    "changeme",
    "change-me",
    "example",
    "example-value",
    "placeholder",
    "replace-me",
    "replace_me",
    "secret",
    "test",
    "todo",
    "your-value",
    "your_value",
}


@dataclass(frozen=True)
class ValidationIssue:
    variable: str
    message: str
    severity: str


@dataclass
class ConfigurationValidationReport:
    environment: str
    valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "environment": self.environment,
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
        }


_LAST_REPORT: ConfigurationValidationReport | None = None


def _environment() -> str:
    return os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).strip().lower()


def _value(name: str) -> str:
    return os.getenv(name, "").strip()


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False

    if normalized in PLACEHOLDER_VALUES:
        return True

    return any(
        token in normalized
        for token in (
            "<replace",
            "<your",
            "your_",
            "your-",
            "example.com",
            "insert_here",
            "insert-here",
        )
    )


def _is_true(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _add_error(
    report: ConfigurationValidationReport,
    variable: str,
    message: str,
) -> None:
    report.errors.append(
        ValidationIssue(
            variable=variable,
            message=message,
            severity="error",
        )
    )


def _add_warning(
    report: ConfigurationValidationReport,
    variable: str,
    message: str,
) -> None:
    report.warnings.append(
        ValidationIssue(
            variable=variable,
            message=message,
            severity="warning",
        )
    )


def _require_non_placeholder(
    report: ConfigurationValidationReport,
    variable: str,
) -> str:
    value = _value(variable)

    if not value:
        _add_error(report, variable, "Required environment variable is missing.")
        return ""

    if _is_placeholder(value):
        _add_error(report, variable, "Environment variable contains a placeholder value.")
        return ""

    return value


def validate_configuration() -> ConfigurationValidationReport:
    environment = _environment()
    production = environment in {"production", "prod"}

    report = ConfigurationValidationReport(
        environment=environment,
        valid=True,
    )

    if environment not in {"development", "dev", "test", "testing", "production", "prod"}:
        _add_warning(
            report,
            "ENVIRONMENT",
            "Unrecognized environment name. Expected development, test or production.",
        )

    log_level = _value("LOG_LEVEL") or "INFO"
    if log_level.upper() not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        _add_error(
            report,
            "LOG_LEVEL",
            "LOG_LEVEL must be CRITICAL, ERROR, WARNING, INFO or DEBUG.",
        )

    database_url = _value("DATABASE_URL")
    if production:
        database_url = _require_non_placeholder(report, "DATABASE_URL")
        if database_url and not database_url.lower().startswith(
            ("postgresql://", "postgres://", "postgresql+")
        ):
            _add_error(
                report,
                "DATABASE_URL",
                "Production DATABASE_URL must use PostgreSQL.",
            )
    elif not database_url:
        _add_warning(
            report,
            "DATABASE_URL",
            "DATABASE_URL is not set. Local fallback behavior will be used.",
        )

    if production:
        _require_non_placeholder(report, "OPENAI_API_KEY")
        _require_non_placeholder(report, "FIREBASE_PROJECT_ID")
        _require_non_placeholder(report, "FIREBASE_STORAGE_BUCKET")

        firebase_credentials = _value("FIREBASE_CREDENTIALS")
        google_credentials = _value("GOOGLE_APPLICATION_CREDENTIALS")

        if not firebase_credentials and not google_credentials:
            _add_error(
                report,
                "FIREBASE_CREDENTIALS",
                "Set FIREBASE_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS.",
            )
        elif firebase_credentials:
            if _is_placeholder(firebase_credentials):
                _add_error(
                    report,
                    "FIREBASE_CREDENTIALS",
                    "FIREBASE_CREDENTIALS contains a placeholder value.",
                )
            else:
                try:
                    parsed_credentials = json.loads(firebase_credentials)
                    if not isinstance(parsed_credentials, dict):
                        raise ValueError
                except (json.JSONDecodeError, ValueError):
                    _add_error(
                        report,
                        "FIREBASE_CREDENTIALS",
                        "FIREBASE_CREDENTIALS must contain a valid JSON object.",
                    )

        billing_provider = (_value("BILLING_PROVIDER") or "paypal").lower()
        if billing_provider != "paypal":
            _add_error(
                report,
                "BILLING_PROVIDER",
                "TalentMatch Pro production billing provider must be paypal.",
            )

        paypal_environment = (_value("PAYPAL_ENV") or "live").lower()
        if paypal_environment != "live":
            _add_error(
                report,
                "PAYPAL_ENV",
                "Production PAYPAL_ENV must be live.",
            )

        _require_non_placeholder(report, "PAYPAL_CLIENT_ID")
        _require_non_placeholder(report, "PAYPAL_CLIENT_SECRET")
        _require_non_placeholder(report, "PAYPAL_PLAN_ID")
        _require_non_placeholder(report, "PAYPAL_WEBHOOK_ID")

        frontend_url = _require_non_placeholder(report, "FRONTEND_URL")
        if frontend_url and not _is_https_url(frontend_url):
            _add_error(
                report,
                "FRONTEND_URL",
                "Production FRONTEND_URL must be a valid HTTPS URL.",
            )

        if not _is_true("FORCE_HTTPS", default=True):
            _add_error(
                report,
                "FORCE_HTTPS",
                "FORCE_HTTPS cannot be disabled in production.",
            )

        if not _is_true("ENABLE_HSTS", default=True):
            _add_error(
                report,
                "ENABLE_HSTS",
                "ENABLE_HSTS cannot be disabled in production.",
            )

        if not _is_true("ENABLE_RATE_LIMITING", default=True):
            _add_error(
                report,
                "ENABLE_RATE_LIMITING",
                "ENABLE_RATE_LIMITING cannot be disabled in production.",
            )

    allowed_hosts = _value("ALLOWED_HOSTS")
    if allowed_hosts:
        hosts = [item.strip().lower() for item in allowed_hosts.split(",") if item.strip()]
        if "*" in hosts:
            _add_error(
                report,
                "ALLOWED_HOSTS",
                "Wildcard '*' is not allowed in ALLOWED_HOSTS.",
            )
        if production and "api.talentmatchcv.com" not in hosts:
            _add_warning(
                report,
                "ALLOWED_HOSTS",
                "api.talentmatchcv.com is not explicitly listed.",
            )
    elif production:
        _add_warning(
            report,
            "ALLOWED_HOSTS",
            "ALLOWED_HOSTS is not explicitly set; application defaults are active.",
        )

    cors_origins = _value("CORS_ORIGINS")
    if cors_origins:
        origins = [item.strip() for item in cors_origins.split(",") if item.strip()]
        for origin in origins:
            if not _is_http_url(origin):
                _add_error(
                    report,
                    "CORS_ORIGINS",
                    f"Invalid CORS origin: {origin}",
                )
            elif production and not origin.startswith("https://"):
                _add_error(
                    report,
                    "CORS_ORIGINS",
                    f"Production CORS origin must use HTTPS: {origin}",
                )
    elif production:
        _add_warning(
            report,
            "CORS_ORIGINS",
            "CORS_ORIGINS is not explicitly set; application defaults are active.",
        )

    report.valid = not report.errors
    return report


def validate_startup_configuration(
    logger: logging.Logger,
) -> ConfigurationValidationReport:
    global _LAST_REPORT

    report = validate_configuration()
    _LAST_REPORT = report

    for warning in report.warnings:
        logger.warning(
            "Configuration validation warning: %s",
            warning.message,
            extra={"event": "configuration_warning"},
        )

    if report.errors:
        for error in report.errors:
            logger.error(
                "Configuration validation error for %s: %s",
                error.variable,
                error.message,
                extra={"event": "configuration_error"},
            )

        if report.environment in {"production", "prod"}:
            variable_names = ", ".join(sorted({issue.variable for issue in report.errors}))
            raise RuntimeError(
                "Production configuration validation failed for: "
                f"{variable_names}. Secret values were not logged."
            )

    logger.info(
        "Configuration validation completed.",
        extra={"event": "configuration_validated"},
    )
    return report


def get_configuration_validation_status() -> dict:
    report = _LAST_REPORT or validate_configuration()
    return {
        "valid": report.valid,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
    }
