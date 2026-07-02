"""In-memory token bucket rate limiter for FastAPI.

No external dependencies. Suitable for single-instance deployment (ECS Fargate).
For multi-instance, replace with Redis-backed limiter.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

import fastapi


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


@dataclass
class RateLimiter:
    """Token bucket rate limiter.

    Args:
        max_requests: Maximum burst size (bucket capacity).
        window_seconds: Time window to refill the full bucket.
    """

    max_requests: int = 5
    window_seconds: int = 60
    _buckets: dict[str, _Bucket] = field(default_factory=dict, init=False, repr=False)

    def _refill(self, bucket: _Bucket) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        refill_rate = self.max_requests / self.window_seconds
        bucket.tokens = min(self.max_requests, bucket.tokens + elapsed * refill_rate)
        bucket.last_refill = now

    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed and consume a token."""
        if key not in self._buckets:
            self._buckets[key] = _Bucket(tokens=self.max_requests, last_refill=time.monotonic())

        bucket = self._buckets[key]
        self._refill(bucket)

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True
        return False

    def remaining(self, key: str) -> int:
        """Return remaining tokens for a key (for headers)."""
        if key not in self._buckets:
            return self.max_requests
        bucket = self._buckets[key]
        self._refill(bucket)
        return int(bucket.tokens)


# Pre-configured limiters for different endpoint tiers
optimize_limiter = RateLimiter(max_requests=5, window_seconds=60)   # 5 sweeps/min
simulate_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 sims/min
export_limiter = RateLimiter(max_requests=3, window_seconds=60)     # 3 exports/min


def get_client_ip(request: fastapi.Request) -> str:
    """Extract client IP, respecting X-Forwarded-For from ALB."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(limiter: RateLimiter, request: fastapi.Request) -> None:
    """Raise 429 if rate limit exceeded."""
    ip = get_client_ip(request)
    if not limiter.is_allowed(ip):
        raise fastapi.HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before retrying.",
        )
