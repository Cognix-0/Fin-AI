"""
In-memory login throttling.

Tracks failed logins per (client IP, email). After `login_max_attempts` failures
within the lockout window, further attempts get 429 until the window passes.

This is per-process: with several workers/replicas, swap it for a shared store
such as Redis.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import status

from app.core.config import settings
from app.core.errors import AppError


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
        return q

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.max_attempts:
                retry_after = int(self.window - (now - q[0])) + 1
                raise AppError(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "TOO_MANY_ATTEMPTS",
                    f"Too many failed login attempts. Try again in {max(1, retry_after // 60)} minute(s).",
                )

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter(
    max_attempts=settings.login_max_attempts,
    window_seconds=settings.login_lockout_minutes * 60,
)
