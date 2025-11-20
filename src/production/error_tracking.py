"""
Error Tracking and Monitoring with Sentry
==========================================

Provides centralized error tracking and monitoring for production.
Integrates with Sentry to capture exceptions, track performance, and alert on issues.

Usage:
    # Initialize at app startup:
    from production.error_tracking import init_error_tracking

    @app.on_event("startup")
    async def startup_event():
        init_error_tracking(app)

    # Track errors with context:
    from production.error_tracking import track_error

    try:
        process_order()
    except Exception as e:
        track_error(e, {"order_id": 12345, "user": "customer@example.com"})
        raise
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import os
import logging

logger = logging.getLogger(__name__)


def init_error_tracking(app=None):
    """
    Initialize Sentry error tracking for production.

    Environment variables required:
        SENTRY_DSN: Sentry project DSN
        ENVIRONMENT: production/staging/development

    Args:
        app: FastAPI application instance (optional)

    Example:
        @app.on_event("startup")
        async def startup_event():
            init_error_tracking(app)
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        logger.warning("SENTRY_DSN not configured - error tracking disabled")
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration()
        ],
        # Add custom tags
        before_send=add_custom_context,
        # Don't send PII
        send_default_pii=False
    )

    logger.info(f"Sentry initialized for environment: {environment}")


def add_custom_context(event, hint):
    """
    Add custom context to Sentry events and mask sensitive data.

    Args:
        event: Sentry event dict
        hint: Additional hint data

    Returns:
        Modified event dict
    """
    # Add business context
    if 'request' in event:
        event['tags'] = event.get('tags', {})
        event['tags']['api_version'] = 'v1'

    # Mask sensitive data
    if 'user' in event and 'email' in event['user']:
        event['user']['email'] = '***@***'

    return event


def track_error(exception: Exception, context: dict = None):
    """
    Manually track an error with additional context.

    This function captures exceptions with custom context for better debugging.
    Use this when you want to add business context to automatic error tracking.

    Args:
        exception: Exception to track
        context: Additional context dict (order_id, user_id, etc.)

    Example:
        try:
            create_order(order_data)
        except Exception as e:
            track_error(e, {
                "order_id": 12345,
                "outlet_name": "A&W - Jewel",
                "line_items_count": 5
            })
            raise
    """
    with sentry_sdk.push_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_exception(exception)
        logger.error(f"Error tracked to Sentry: {str(exception)}", exc_info=True)
