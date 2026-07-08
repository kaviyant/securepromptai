from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, List

class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, 
        app, 
        requests_limit: int = 100, 
        window_seconds: int = 60
    ):
        """
        Initializes RateLimiting parameters.
        Default: Max 100 requests per 60 seconds per IP.
        """
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # In-memory database mapping: Client IP -> List of timestamps
        self.ip_records: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude Swagger documents/redoc and static pages from rate limiting
        path = request.url.path
        if path.startswith("/docs") or path.startswith("/openapi.json") or path.startswith("/redoc") or path == "/":
            return await call_next(request)

        # Retrieve client IP
        client_ip = request.client.host if request.client else "unknown_ip"
        current_time = time.time()

        # Get records for the client IP, initializing if needed
        timestamps = self.ip_records.get(client_ip, [])

        # Filter out timestamps older than the sliding window boundary
        window_start = current_time - self.window_seconds
        timestamps = [ts for ts in timestamps if ts > window_start]

        # Check if client exceeds limit
        if len(timestamps) >= self.requests_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Too many requests. Please try again later."
                },
                headers={
                    "Retry-After": str(self.window_seconds)
                }
            )

        # Record this request
        timestamps.append(current_time)
        self.ip_records[client_ip] = timestamps

        # Proceed to next route handler
        return await call_next(request)
