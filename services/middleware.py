import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.logging_config import logger  # 위에서 만든 logger import


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        logger.info(f"[Request] {request.method} {request.url.path}")
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        logger.info(
            f"[Response] {request.method} {request.url.path} completed in {duration:.1f}ms with status {response.status_code}"
        )
        return response
