"""
Idempotency Middleware for Duplicate Request Prevention
=======================================================

Prevents duplicate order creation when users retry requests.
Uses Redis to cache successful responses keyed by idempotency key.

Usage:
    # In FastAPI app:
    from production.idempotency import IdempotencyMiddleware

    app.add_middleware(IdempotencyMiddleware)

    # Client must send unique key:
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    requests.post("/api/chatbot", headers=headers, ...)
"""

import hashlib
import json
import uuid
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response, HTTPException, Header
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import logging

logger = logging.getLogger(__name__)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to prevent duplicate request processing.

    Caches successful responses in Redis keyed by idempotency key.
    If same key is used again within TTL, returns cached response.
    """

    # Idempotent methods (only these are checked)
    IDEMPOTENT_METHODS = {'POST', 'PUT', 'PATCH'}

    # Paths that require idempotency
    IDEMPOTENT_PATHS = {'/api/chatbot', '/api/orders'}

    def __init__(self, app, redis_client: redis.Redis = None, ttl_seconds: int = 86400):
        """
        Initialize idempotency middleware.

        Args:
            app: FastAPI application
            redis_client: Redis client (optional, will create if not provided)
            ttl_seconds: Time-to-live for cached responses (default 24 hours)
        """
        super().__init__(app)
        self.redis = redis_client or self._get_redis_client()
        self.ttl = ttl_seconds

    def _get_redis_client(self) -> redis.Redis:
        """Get Redis client from config"""
        try:
            from config import config
            return redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with idempotency check.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response (either cached or freshly processed)
        """
        # Only check idempotency for specific methods and paths
        if request.method not in self.IDEMPOTENT_METHODS:
            return await call_next(request)

        if not any(request.url.path.startswith(path) for path in self.IDEMPOTENT_PATHS):
            return await call_next(request)

        # Get idempotency key from header
        idempotency_key = request.headers.get('Idempotency-Key')

        if not idempotency_key:
            # Require idempotency key for protected endpoints
            return JSONResponse(
                status_code=400,
                content={
                    'error': 'Idempotency-Key header is required',
                    'detail': 'Send a unique UUID in Idempotency-Key header'
                }
            )

        # Validate idempotency key format
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    'error': 'Invalid Idempotency-Key format',
                    'detail': 'Idempotency-Key must be a valid UUID'
                }
            )

        # Generate cache key (include user ID for multi-tenant isolation)
        user_id = getattr(request.state, 'user_id', 'anonymous')
        cache_key = f"idempotency:{user_id}:{idempotency_key}"

        # Check for cached response
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
            return JSONResponse(
                status_code=cached_response['status_code'],
                content=cached_response['body'],
                headers=cached_response.get('headers', {})
            )

        # Process request
        response = await call_next(request)

        # Cache successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            await self._cache_response(cache_key, response)

        return response

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response from Redis.

        Args:
            cache_key: Redis key for cached response

        Returns:
            Cached response dict or None if not found
        """
        try:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Error retrieving cached response: {e}")

        return None

    async def _cache_response(self, cache_key: str, response: Response) -> None:
        """
        Cache successful response in Redis.

        Args:
            cache_key: Redis key for caching
            response: HTTP response to cache
        """
        try:
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Parse JSON body
            try:
                body_json = json.loads(body.decode())
            except json.JSONDecodeError:
                body_json = body.decode()

            # Cache response data
            cache_data = {
                'status_code': response.status_code,
                'body': body_json,
                'headers': dict(response.headers)
            }

            self.redis.setex(cache_key, self.ttl, json.dumps(cache_data))
            logger.info(f"Cached response for key: {cache_key}")

            # Restore body for actual response
            response.body_iterator = self._make_body_iterator(body)

        except Exception as e:
            logger.error(f"Error caching response: {e}")

    @staticmethod
    async def _make_body_iterator(body: bytes):
        """Create async iterator from bytes"""
        yield body


# Dependency injection for route-level idempotency
def require_idempotency_key(idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    """
    Dependency to require idempotency key on specific routes.

    Usage:
        @app.post("/api/orders")
        async def create_order(
            order: OrderRequest,
            idempotency_key: str = Depends(require_idempotency_key)
        ):
            ...
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required"
        )

    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key must be a valid UUID"
        )

    return idempotency_key
