import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Ephemeral in-memory sliding window rate limiter (zero disk logging)
class InMemoryRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)

    def is_allowed(self, client_key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        # Clean timestamps older than window
        self.requests[client_key] = [t for t in self.requests[client_key] if now - t < window_seconds]
        if len(self.requests[client_key]) >= limit:
            return False
        self.requests[client_key].append(now)
        return True

rate_limiter = InMemoryRateLimiter()

class AnonymityAndSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Ephemeral rate limiting per path category
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # Enforce rate limits
        if request.method == "POST" and path.endswith("/reports"):
            # Max 15 submissions per minute per client
            if not rate_limiter.is_allowed(f"submit:{client_host}", limit=15, window_seconds=60):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many report submissions. Please wait before submitting again.", "error_code": "RATE_LIMITED"}
                )
        elif request.method == "GET" and "/reports/WD-" in path:
            # Max 60 tracking lookups per minute to prevent brute-force
            if not rate_limiter.is_allowed(f"track:{client_host}", limit=60, window_seconds=60):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded for case lookups.", "error_code": "RATE_LIMITED"}
                )

        # 2. Process request without attaching IP or user-agent to the downstream state
        response: Response = await call_next(request)

        # 3. Add strict anonymity & security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        
        return response
