from __future__ import annotations

import os
import platform
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


AI_PATHS = {
    "/analyze-resume",
    "/analyze-test",
    "/ats-check",
    "/ats-test",
    "/semantic-match",
    "/recruiter/rank-candidates",
    "/rewrite-cv",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_process_memory_bytes() -> int | None:
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        value = int(usage.ru_maxrss)

        if sys.platform == "darwin":
            return value

        return value * 1024
    except Exception:
        return None


@dataclass
class ApplicationMetrics:
    started_monotonic: float = field(default_factory=time.monotonic)
    started_at: str = field(default_factory=utc_now_iso)
    requests_total: int = 0
    requests_success: int = 0
    requests_client_error: int = 0
    requests_server_error: int = 0
    ai_requests_total: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_request_at: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_request(
        self,
        *,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self.requests_total += 1
            self.total_duration_ms += max(duration_ms, 0.0)
            self.max_duration_ms = max(self.max_duration_ms, duration_ms)
            self.last_request_at = utc_now_iso()

            if 200 <= status_code < 400:
                self.requests_success += 1
            elif 400 <= status_code < 500:
                self.requests_client_error += 1
            elif status_code >= 500:
                self.requests_server_error += 1

            if path in AI_PATHS:
                self.ai_requests_total += 1

    def snapshot(
        self,
        *,
        environment: str,
        database_ok: bool | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            uptime_seconds = max(0.0, time.monotonic() - self.started_monotonic)
            average_duration_ms = (
                self.total_duration_ms / self.requests_total
                if self.requests_total
                else 0.0
            )

            payload: dict[str, Any] = {
                "observability_enabled": True,
                "environment": environment,
                "started_at": self.started_at,
                "uptime_seconds": round(uptime_seconds, 2),
                "requests_total": self.requests_total,
                "requests_success": self.requests_success,
                "requests_client_error": self.requests_client_error,
                "requests_server_error": self.requests_server_error,
                "ai_requests_total": self.ai_requests_total,
                "average_request_duration_ms": round(average_duration_ms, 2),
                "max_request_duration_ms": round(self.max_duration_ms, 2),
                "last_request_at": self.last_request_at,
                "runtime": {
                    "python_version": platform.python_version(),
                    "implementation": platform.python_implementation(),
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "machine": platform.machine(),
                    "pid": os.getpid(),
                    "cpu_count": os.cpu_count(),
                    "process_memory_bytes": get_process_memory_bytes(),
                },
            }

            if database_ok is not None:
                payload["database_ok"] = database_ok

            return payload


METRICS = ApplicationMetrics()
