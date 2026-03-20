"""Simple in-memory IP-based rate limiter. No external dependencies."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException


class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
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
