from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import os
import threading
import time

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class SecuritySettings:
    auth_mode: str
    api_key: str | None
    api_key_header: str
    rate_limit_enabled: bool
    rate_limit_max_requests: int
    rate_limit_window_seconds: int


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_security_settings() -> SecuritySettings:
    auth_mode = os.getenv("AGENT_AUTH_MODE", "disabled").strip().lower()
    if auth_mode not in {"disabled", "api_key"}:
        raise ValueError("Invalid AGENT_AUTH_MODE. Allowed: disabled, api_key")

    api_key = os.getenv("AGENT_API_KEY")
    if auth_mode == "api_key" and not (api_key or "").strip():
        raise ValueError("AGENT_API_KEY is required when AGENT_AUTH_MODE=api_key")

    api_key_header = os.getenv("AGENT_API_KEY_HEADER", "X-API-Key").strip()
    if not api_key_header:
        api_key_header = "X-API-Key"

    rate_limit_enabled = _parse_bool(os.getenv("AGENT_RATE_LIMIT_ENABLED"), True)
    rate_limit_max_requests = int(os.getenv("AGENT_RATE_LIMIT_MAX_REQUESTS", "10"))
    rate_limit_window_seconds = int(
        os.getenv("AGENT_RATE_LIMIT_WINDOW_SECONDS", "60")
    )

    if rate_limit_max_requests < 1:
        raise ValueError("AGENT_RATE_LIMIT_MAX_REQUESTS must be >= 1")
    if rate_limit_window_seconds < 1:
        raise ValueError("AGENT_RATE_LIMIT_WINDOW_SECONDS must be >= 1")

    return SecuritySettings(
        auth_mode=auth_mode,
        api_key=(api_key or "").strip() or None,
        api_key_header=api_key_header,
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_max_requests=rate_limit_max_requests,
        rate_limit_window_seconds=rate_limit_window_seconds,
    )


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float | None = None,
    ) -> bool:
        current = now if now is not None else time.time()
        threshold = current - float(window_seconds)

        with self._lock:
            queue = self._events[key]

            while queue and queue[0] <= threshold:
                queue.popleft()

            if len(queue) >= max_requests:
                return False

            queue.append(current)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_RATE_LIMITER = SlidingWindowRateLimiter()


def reset_rate_limiter() -> None:
    _RATE_LIMITER.reset()


def enforce_request_security(request: Request) -> None:
    settings = load_security_settings()

    if settings.auth_mode == "api_key":
        provided = request.headers.get(settings.api_key_header)
        if not provided or provided != settings.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
            )

    if settings.rate_limit_enabled:
        client_key = request.client.host if request.client else "unknown"
        allowed = _RATE_LIMITER.allow(
            key=client_key,
            max_requests=settings.rate_limit_max_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )
