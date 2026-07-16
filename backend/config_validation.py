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

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

SUPPORTED_ENVIRONMENTS = {
    "development",
    "dev",
    "test",
    "testing",
    "production",
    "prod",
}

DATABASE_INTEGER_RULES: dict[str, tuple[int, int, int]] = {
    "DB_POOL_SIZE": (5, 1, 50),
    "DB_MAX_OVERFLOW": (10, 0, 100),
    "DB_POOL_TIMEOUT_SECONDS": (30, 1, 300),
    "DB_POOL_RECYCLE_SECONDS": (300, 30, 86_400),
    "DB_CONNECT_TIMEOUT_SECONDS": (10, 1, 120),
    "DB_STATEMENT_TIMEOUT_MS": (30_000, 1_000, 300_000),
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
    database_values: dict[str, int | bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [asdict(issue) for issue in self.errors],
            "warnings": [asdict(issue) for issue in self.warnings],
            "database_configuration_validation_enabled": True,
            "database_values": dict(self.database_values),
        }


_LAST_REPORT: ConfigurationValidationReport | None = None


def _environment() -> str:
    return os.getenv(
        "ENVIRONMENT",
        os.getenv("APP_ENV", "development"),
    ).strip().lower()


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
        _add_error(
            report,
            variable,
            "Required environment variable is missing.",
        )
        return ""

    if _is_placeholder(value):
        _add_error(
            report,
            variable,
            "Environment variable contains a placeholder value.",
        )
        return ""

    return value


def _validate_boolean(
    report: ConfigurationValidationReport,
    variable: str,
    *,
    default: bool,
) -> bool:
    raw = os.getenv(variable)

    if raw is None:
        return default

    normalized = raw.strip().lower()

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    _add_error(
        report,
        variable,
        (
            f"{variable} must be one of: "
            "true, false, 1, 0, yes, no, on, off."
        ),
    )
    return default


def _validate_integer(
    report: ConfigurationValidationReport,
    variable: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(variable)

    if raw is None or not raw.strip():
        return default

    try:
        value = int(raw.strip())
    except ValueError:
        _add_error(
            report,
            variable,
            (
                f"{variable} must be an integer between "
                f"{minimum} and {maximum}."
            ),
        )
        return default

    if value < minimum or value > maximum:
        _add_error(
            report,
            variable,
            f"{variable} must be between {minimum} and {maximum}.",
        )
        return default

    return value


def _validate_database_configuration(
    report: ConfigurationValidationReport,
    *,
    production: bool,
) -> None:
    database_url = _value("DATABASE_URL")

    if production:
        database_url = _require_non_placeholder(
            report,
            "DATABASE_URL",
        )

        if database_url and not database_url.lower().startswith(
            (
                "postgresql://",
                "postgres://",
                "postgresql+psycopg://",
            )
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

    parsed_values: dict[str, int | bool] = {}

    for variable, (default, minimum, maximum) in DATABASE_INTEGER_RULES.items():
        parsed_values[variable] = _validate_integer(
            report,
            variable,
            default=default,
            minimum=minimum,
            maximum=maximum,
        )

    db_echo = _validate_boolean(
        report,
        "DB_ECHO",
        default=False,
    )
    parsed_values["DB_ECHO"] = db_echo

    pool_size = int(parsed_values["DB_POOL_SIZE"])
    max_overflow = int(parsed_values["DB_MAX_OVERFLOW"])
    connect_timeout_seconds = int(
        parsed_values["DB_CONNECT_TIMEOUT_SECONDS"]
    )
    statement_timeout_ms = int(
        parsed_values["DB_STATEMENT_TIMEOUT_MS"]
    )

    if pool_size + max_overflow > 100:
        _add_error(
            report,
            "DB_MAX_OVERFLOW",
            (
                "DB_POOL_SIZE + DB_MAX_OVERFLOW must not exceed 100 "
                "connections per application instance."
            ),
        )

    if statement_timeout_ms <= connect_timeout_seconds * 1_000:
        _add_error(
            report,
            "DB_STATEMENT_TIMEOUT_MS",
            (
                "DB_STATEMENT_TIMEOUT_MS must be greater than "
                "DB_CONNECT_TIMEOUT_SECONDS expressed in milliseconds."
            ),
        )

    if production and db_echo:
        _add_error(
            report,
            "DB_ECHO",
            "DB_ECHO cannot be enabled in production.",
        )

    report.database_values = parsed_values


def _validate_firebase_credentials(
    report: ConfigurationValidationReport,
) -> None:
    firebase_credentials = _value("FIREBASE_CREDENTIALS")
    google_credentials = _value("GOOGLE_APPLICATION_CREDENTIALS")

    if not firebase_credentials and not google_credentials:
        _add_error(
            report,
            "FIREBASE_CREDENTIALS",
            "Set FIREBASE_CREDENTIALS or GOOGLE_APPLICATION_CREDENTIALS.",
        )
        return

    if firebase_credentials:
        if _is_placeholder(firebase_credentials):
            _add_error(
                report,
                "FIREBASE_CREDENTIALS",
                "FIREBASE_CREDENTIALS contains a placeholder value.",
            )
            return

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

    if google_credentials and _is_placeholder(google_credentials):
        _add_error(
            report,
            "GOOGLE_APPLICATION_CREDENTIALS",
            (
                "GOOGLE_APPLICATION_CREDENTIALS contains a placeholder "
                "value."
            ),
        )


def _validate_production_configuration(
    report: ConfigurationValidationReport,
) -> None:
    _require_non_placeholder(report, "OPENAI_API_KEY")
    _require_non_placeholder(report, "FIREBASE_PROJECT_ID")
    _require_non_placeholder(report, "FIREBASE_STORAGE_BUCKET")
    _validate_firebase_credentials(report)

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

    force_https = _validate_boolean(
        report,
        "FORCE_HTTPS",
        default=True,
    )
    enable_hsts = _validate_boolean(
        report,
        "ENABLE_HSTS",
        default=True,
    )
    enable_rate_limiting = _validate_boolean(
        report,
        "ENABLE_RATE_LIMITING",
        default=True,
    )

    if not force_https:
        _add_error(
            report,
            "FORCE_HTTPS",
            "FORCE_HTTPS cannot be disabled in production.",
        )

    if not enable_hsts:
        _add_error(
            report,
            "ENABLE_HSTS",
            "ENABLE_HSTS cannot be disabled in production.",
        )

    if not enable_rate_limiting:
        _add_error(
            report,
            "ENABLE_RATE_LIMITING",
            "ENABLE_RATE_LIMITING cannot be disabled in production.",
        )


def _validate_hosts_and_cors(
    report: ConfigurationValidationReport,
    *,
    production: bool,
) -> None:
    allowed_hosts = _value("ALLOWED_HOSTS")

    if allowed_hosts:
        hosts = [
            item.strip().lower()
            for item in allowed_hosts.split(",")
            if item.strip()
        ]

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
            (
                "ALLOWED_HOSTS is not explicitly set; "
                "application defaults are active."
            ),
        )

    cors_origins = _value("CORS_ORIGINS")

    if cors_origins:
        origins = [
            item.strip()
            for item in cors_origins.split(",")
            if item.strip()
        ]

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
                    (
                        "Production CORS origin must use HTTPS: "
                        f"{origin}"
                    ),
                )
    elif production:
        _add_warning(
            report,
            "CORS_ORIGINS",
            (
                "CORS_ORIGINS is not explicitly set; "
                "application defaults are active."
            ),
        )


def validate_configuration() -> ConfigurationValidationReport:
    environment = _environment()
    production = environment in {"production", "prod"}

    report = ConfigurationValidationReport(
        environment=environment,
        valid=True,
    )

    if environment not in SUPPORTED_ENVIRONMENTS:
        _add_warning(
            report,
            "ENVIRONMENT",
            (
                "Unrecognized environment name. Expected development, "
                "test or production."
            ),
        )

    log_level = _value("LOG_LEVEL") or "INFO"
    if log_level.upper() not in {
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
    }:
        _add_error(
            report,
            "LOG_LEVEL",
            (
                "LOG_LEVEL must be CRITICAL, ERROR, WARNING, "
                "INFO or DEBUG."
            ),
        )

    _validate_database_configuration(
        report,
        production=production,
    )

    if production:
        _validate_production_configuration(report)
    else:
        _validate_boolean(
            report,
            "FORCE_HTTPS",
            default=False,
        )
        _validate_boolean(
            report,
            "ENABLE_HSTS",
            default=False,
        )
        _validate_boolean(
            report,
            "ENABLE_RATE_LIMITING",
            default=True,
        )

    _validate_hosts_and_cors(
        report,
        production=production,
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
            extra={
                "event": "configuration_warning",
                "configuration_variable": warning.variable,
            },
        )

    if report.errors:
        for error in report.errors:
            logger.error(
                "Configuration validation error for %s: %s",
                error.variable,
                error.message,
                extra={
                    "event": "configuration_error",
                    "configuration_variable": error.variable,
                },
            )

        if report.environment in {"production", "prod"}:
            variable_names = ", ".join(
                sorted(
                    {
                        issue.variable
                        for issue in report.errors
                    }
                )
            )
            raise RuntimeError(
                "Production configuration validation failed for: "
                f"{variable_names}. Secret values were not logged."
            )

    logger.info(
        "Configuration validation completed.",
        extra={
            "event": "configuration_validated",
        },
    )

    return report


def get_configuration_validation_status() -> dict[str, object]:
    report = _LAST_REPORT or validate_configuration()

    return {
        "environment": report.environment,
        "valid": report.valid,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "database_configuration_validation_enabled": True,
    }
