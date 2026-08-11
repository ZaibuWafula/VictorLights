"""
ratelimit.py — a deliberately simple in-memory sliding-window limiter.
No Redis, no extra package: fine for a single small-instance deployment.
If you later run multiple instances behind a load balancer, swap this for
a shared store (Redis) so limits are counted across instances.
"""
import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, window_seconds: int, max_requests: int, path_prefix: str = "/api"):
        super().__init__(app)
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.path_prefix = path_prefix
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if not request.url.path.startswith(self.path_prefix):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self.hits[client_ip]

        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return JSONResponse(status_code=429, content={"error": "Too many requests, please slow down"})

        bucket.append(now)
        return await call_next(request)
