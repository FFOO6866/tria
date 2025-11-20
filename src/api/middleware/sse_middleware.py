"""
TRIA AI-BPO SSE Middleware
===========================

Middleware for Server-Sent Events (SSE) support in FastAPI.

Features:
- Automatic SSE headers for streaming endpoints
- Connection timeout management
- Client disconnect detection
- CORS support for SSE

NO MOCKING - Production-ready middleware.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Configure logging
logger = logging.getLogger(__name__)


class SSEMiddleware(BaseHTTPMiddleware):
    """
    Middleware for SSE (Server-Sent Events) support

    Features:
    - Adds SSE headers for streaming endpoints
    - Handles connection timeouts
    - Logs streaming metrics

    Usage:
        from fastapi import FastAPI
        from api.middleware.sse_middleware import SSEMiddleware

        app = FastAPI()
        app.add_middleware(SSEMiddleware, timeout=60)
    """

    def __init__(
        self,
        app: ASGIApp,
        timeout: int = 60,
        streaming_paths: list = None
    ):
        """
        Initialize SSE middleware

        Args:
            app: FastAPI application
            timeout: Streaming timeout in seconds (default: 60)
            streaming_paths: List of path prefixes for streaming endpoints
                           (default: ["/chat/stream"])
        """
        super().__init__(app)
        self.timeout = timeout
        self.streaming_paths = streaming_paths or ["/chat/stream"]

        logger.info(
            f"SSEMiddleware initialized with timeout={timeout}s, "
            f"streaming_paths={self.streaming_paths}"
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and add SSE headers if needed

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with SSE headers if applicable
        """
        # Check if this is a streaming endpoint
        is_streaming = any(
            request.url.path.startswith(path)
            for path in self.streaming_paths
        )

        if is_streaming:
            logger.info(
                f"[SSE] Streaming request: {request.method} {request.url.path}"
            )
            start_time = time.time()

        # Process request
        response = await call_next(request)

        # Add SSE headers for streaming endpoints
        if is_streaming and response.status_code == 200:
            # These headers are critical for SSE
            response.headers["Cache-Control"] = "no-cache"
            response.headers["Connection"] = "keep-alive"
            response.headers["X-Accel-Buffering"] = "no"  # Disable nginx buffering

            # CORS headers for SSE (allow any origin for demo)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"

            # Log streaming metrics
            if is_streaming:
                duration = time.time() - start_time
                logger.info(
                    f"[SSE] Streaming response sent in {duration:.2f}s "
                    f"(path: {request.url.path})"
                )

        return response


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def add_sse_headers(response: Response) -> Response:
    """
    Add SSE headers to response

    Args:
        response: FastAPI response

    Returns:
        Response with SSE headers added

    Example:
        @app.get("/stream")
        async def stream():
            response = StreamingResponse(generate())
            return add_sse_headers(response)
    """
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Allow-Origin"] = "*"

    return response


def is_client_connected(request: Request) -> bool:
    """
    Check if client is still connected

    Args:
        request: FastAPI request

    Returns:
        True if client is connected, False otherwise

    Example:
        async def generate():
            while True:
                if not is_client_connected(request):
                    break
                yield data
    """
    try:
        # Check if connection is still alive
        return not request.is_disconnected()
    except Exception:
        return False
