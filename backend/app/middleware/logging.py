from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger("secureprompt")

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Extract HTTP metadata
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # Proceed with request execution
        try:
            response = await call_next(request)
            
            # Calculate execution duration
            duration = round((time.time() - start_time) * 1000, 2)
            
            # Log audit details
            logger.info(
                f"{method} {path} | Client: {client_ip} | Status: {response.status_code} | Latency: {duration}ms"
            )
            
            # Inject custom header showing backend latency
            response.headers["X-Process-Latency-Ms"] = str(duration)
            return response
            
        except Exception as e:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"FAILED {method} {path} | Client: {client_ip} | Latency: {duration}ms | Error: {str(e)}"
            )
            raise e
