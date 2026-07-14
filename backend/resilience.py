from __future__ import annotations

import logging
import os
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    base_delay_seconds: float
    max_delay_seconds: float
    jitter_seconds: float

    def delay_for_attempt(self, attempt: int) -> float:
        exponential_delay = self.base_delay_seconds * (2 ** max(0, attempt - 1))
        bounded_delay = min(exponential_delay, self.max_delay_seconds)
        jitter = random.uniform(0.0, max(0.0, self.jitter_seconds))
        return bounded_delay + jitter


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int
    recovery_timeout_seconds: float
    half_open_success_threshold: int = 1


class ExternalServiceError(RuntimeError):
    def __init__(
        self,
        *,
        service: str,
        message: str,
        error_code: str,
        status_code: int = 503,
        retryable: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.service = service
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


class ExternalServiceTimeoutError(ExternalServiceError):
    def __init__(
        self,
        *,
        service: str,
        message: str,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            service=service,
            message=message,
            error_code="external_service_timeout",
            status_code=503,
            retryable=True,
            retry_after_seconds=retry_after_seconds,
        )


class ExternalServiceUnavailableError(ExternalServiceError):
    def __init__(
        self,
        *,
        service: str,
        message: str,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            service=service,
            message=message,
            error_code="external_service_unavailable",
            status_code=503,
            retryable=True,
            retry_after_seconds=retry_after_seconds,
        )


class CircuitBreakerOpenError(ExternalServiceUnavailableError):
    def __init__(
        self,
        *,
        service: str,
        retry_after_seconds: int,
    ) -> None:
        super().__init__(
            service=service,
            message=f"{service} is temporarily unavailable. Please try again later.",
            retry_after_seconds=retry_after_seconds,
        )
        self.error_code = "circuit_breaker_open"


class CircuitBreaker:
    def __init__(
        self,
        *,
        service: str,
        policy: CircuitBreakerPolicy,
        logger: logging.Logger,
    ) -> None:
        self.service = service
        self.policy = policy
        self.logger = logger
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._opened_at: float | None = None
        self._half_open_probe_in_progress = False
        self._lock = threading.RLock()

    def _seconds_until_retry(self, now: float | None = None) -> int:
        current = now if now is not None else time.monotonic()

        if self._opened_at is None:
            return max(1, int(self.policy.recovery_timeout_seconds))

        elapsed = current - self._opened_at
        remaining = self.policy.recovery_timeout_seconds - elapsed
        return max(1, int(remaining))

    def before_call(self) -> None:
        with self._lock:
            now = time.monotonic()

            if self._state == CircuitState.OPEN:
                if (
                    self._opened_at is not None
                    and now - self._opened_at >= self.policy.recovery_timeout_seconds
                ):
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_success_count = 0
                    self._half_open_probe_in_progress = False
                    self.logger.warning(
                        "Circuit breaker entered half-open state.",
                        extra={
                            "event": "circuit_breaker_half_open",
                            "service": self.service,
                        },
                    )
                else:
                    raise CircuitBreakerOpenError(
                        service=self.service,
                        retry_after_seconds=self._seconds_until_retry(now),
                    )

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_probe_in_progress:
                    raise CircuitBreakerOpenError(
                        service=self.service,
                        retry_after_seconds=max(
                            1,
                            int(self.policy.recovery_timeout_seconds),
                        ),
                    )

                self._half_open_probe_in_progress = True

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_probe_in_progress = False
                self._half_open_success_count += 1

                if (
                    self._half_open_success_count
                    >= self.policy.half_open_success_threshold
                ):
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._half_open_success_count = 0
                    self._opened_at = None
                    self.logger.info(
                        "Circuit breaker closed after successful recovery.",
                        extra={
                            "event": "circuit_breaker_closed",
                            "service": self.service,
                        },
                    )
                return

            self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_probe_in_progress = False
                self._open_circuit()
                return

            self._failure_count += 1

            if self._failure_count >= self.policy.failure_threshold:
                self._open_circuit()

    def _open_circuit(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_success_count = 0
        self._half_open_probe_in_progress = False
        self.logger.error(
            "Circuit breaker opened.",
            extra={
                "event": "circuit_breaker_opened",
                "service": self.service,
            },
        )

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            retry_after_seconds = (
                self._seconds_until_retry()
                if self._state == CircuitState.OPEN
                else None
            )

            return {
                "service": self.service,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.policy.failure_threshold,
                "recovery_timeout_seconds": self.policy.recovery_timeout_seconds,
                "retry_after_seconds": retry_after_seconds,
            }


class ResilienceExecutor(Generic[T]):
    def __init__(
        self,
        *,
        service: str,
        retry_policy: RetryPolicy,
        circuit_breaker: CircuitBreaker,
        logger: logging.Logger,
    ) -> None:
        self.service = service
        self.retry_policy = retry_policy
        self.circuit_breaker = circuit_breaker
        self.logger = logger

    def execute(
        self,
        operation: Callable[[], T],
        *,
        operation_name: str,
        is_retryable: Callable[[Exception], bool],
        translate_error: Callable[[Exception], ExternalServiceError],
        allow_retry: bool = True,
    ) -> T:
        self.circuit_breaker.before_call()
        max_attempts = self.retry_policy.max_retries + 1 if allow_retry else 1

        for attempt in range(1, max_attempts + 1):
            try:
                result = operation()
                self.circuit_breaker.record_success()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception as exc:
                retryable = bool(is_retryable(exc))
                final_attempt = attempt >= max_attempts

                if retryable:
                    self.circuit_breaker.record_failure()

                if not retryable or final_attempt:
                    translated = translate_error(exc)

                    if retryable:
                        self.logger.error(
                            "External service request failed after retries.",
                            extra={
                                "event": "external_service_unavailable",
                                "service": self.service,
                                "operation": operation_name,
                                "attempt": attempt,
                            },
                        )

                    raise translated from exc

                delay_seconds = self.retry_policy.delay_for_attempt(attempt)
                self.logger.warning(
                    "Retrying external service request.",
                    extra={
                        "event": "external_service_retry",
                        "service": self.service,
                        "operation": operation_name,
                        "attempt": attempt,
                        "retry_delay_seconds": round(delay_seconds, 3),
                    },
                )
                time.sleep(delay_seconds)

        raise ExternalServiceUnavailableError(
            service=self.service,
            message=f"{self.service} request failed.",
        )


def get_int_setting(
    name: str,
    default: int,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc

    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}.")

    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be at most {maximum}.")

    return value


def get_float_setting(
    name: str,
    default: float,
    *,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number.") from exc

    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}.")

    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be at most {maximum}.")

    return value


def build_retry_policy(prefix: str) -> RetryPolicy:
    return RetryPolicy(
        max_retries=get_int_setting(
            f"{prefix}_MAX_RETRIES",
            2,
            minimum=0,
            maximum=5,
        ),
        base_delay_seconds=get_float_setting(
            f"{prefix}_RETRY_BASE_DELAY_SECONDS",
            1.0,
            minimum=0.0,
            maximum=30.0,
        ),
        max_delay_seconds=get_float_setting(
            f"{prefix}_RETRY_MAX_DELAY_SECONDS",
            8.0,
            minimum=0.1,
            maximum=60.0,
        ),
        jitter_seconds=get_float_setting(
            f"{prefix}_RETRY_JITTER_SECONDS",
            0.5,
            minimum=0.0,
            maximum=10.0,
        ),
    )


def build_circuit_breaker_policy(prefix: str) -> CircuitBreakerPolicy:
    return CircuitBreakerPolicy(
        failure_threshold=get_int_setting(
            f"{prefix}_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
            5,
            minimum=1,
            maximum=50,
        ),
        recovery_timeout_seconds=get_float_setting(
            f"{prefix}_CIRCUIT_BREAKER_RECOVERY_SECONDS",
            60.0,
            minimum=1.0,
            maximum=3600.0,
        ),
        half_open_success_threshold=get_int_setting(
            f"{prefix}_CIRCUIT_BREAKER_SUCCESS_THRESHOLD",
            1,
            minimum=1,
            maximum=10,
        ),
    )


def build_resilience_executor(
    *,
    service: str,
    prefix: str,
    logger: logging.Logger,
) -> ResilienceExecutor:
    circuit_breaker = CircuitBreaker(
        service=service,
        policy=build_circuit_breaker_policy(prefix),
        logger=logger,
    )

    return ResilienceExecutor(
        service=service,
        retry_policy=build_retry_policy(prefix),
        circuit_breaker=circuit_breaker,
        logger=logger,
    )
