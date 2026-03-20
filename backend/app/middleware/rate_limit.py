"""Simple in-memory IP-based rate limiter. No external dependencies."""
import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException

# Number of trusted reverse proxies (Railway, Render, etc.)
# When > 0, uses the Nth-from-right X-Forwarded-For IP.
# When 0, ignores X-Forwarded-For entirely and uses request.client.host.
TRUSTED_PROXY_COUNT = int(os.getenv("TRUSTED_PROXY_COUNT", "1"))


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if TRUSTED_PROXY_COUNT > 0 and forwarded:
            ips = [ip.strip() for ip in forwarded.split(",")]
            # Rightmost N IPs are from trusted proxies; client is just before them
            idx = max(0, len(ips) - TRUSTED_PROXY_COUNT)
            return ips[idx]
        return request.client.host if request.client else "unknown"

    def check(self, request: Request):
        ip = self._get_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]
        if len(self._requests[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per hour.",
            )
        self._requests[ip].append(now)


chat_limiter = RateLimiter(max_requests=30, window_seconds=3600)
digest_limiter = RateLimiter(max_requests=10, window_seconds=3600)
