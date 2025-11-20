"""
Workflow timeout utility for production safety.

Prevents workflows from hanging indefinitely by enforcing
configurable timeouts on all workflow executions.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, Any, TypeVar, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Default timeout in seconds (can be overridden via environment variable)
DEFAULT_WORKFLOW_TIMEOUT = 60  # 60 seconds


class WorkflowTimeoutError(Exception):
    """Raised when a workflow execution exceeds the configured timeout."""
    pass


def with_timeout(timeout_seconds: int = DEFAULT_WORKFLOW_TIMEOUT):
    """
    Decorator to enforce timeout on workflow executions.

    Args:
        timeout_seconds: Maximum execution time in seconds

    Returns:
        Decorated function with timeout protection

    Raises:
        WorkflowTimeoutError: If execution exceeds timeout

    Example:
        @with_timeout(30)
        def execute_workflow(workflow):
            return runtime.execute(workflow.build())
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    result = future.result(timeout=timeout_seconds)
                    return result
                except FuturesTimeoutError:
                    error_msg = f"Workflow execution exceeded timeout of {timeout_seconds}s"
                    logger.error(
                        f"{error_msg} | function={func.__name__} | args={args[:2]}",  # Log first 2 args only
                        extra={
                            "timeout_seconds": timeout_seconds,
                            "function": func.__name__
                        }
                    )
                    raise WorkflowTimeoutError(error_msg)
                except Exception as e:
                    logger.error(
                        f"Workflow execution failed | function={func.__name__} | error={str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__
                        }
                    )
                    raise
        return wrapper
    return decorator


def execute_with_timeout(
    func: Callable[..., T],
    args: Tuple = (),
    kwargs: dict = None,
    timeout_seconds: int = DEFAULT_WORKFLOW_TIMEOUT
) -> T:
    """
    Execute a function with timeout protection (non-decorator version).

    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        timeout_seconds: Maximum execution time in seconds

    Returns:
        Function result

    Raises:
        WorkflowTimeoutError: If execution exceeds timeout

    Example:
        result = execute_with_timeout(
            runtime.execute,
            args=(workflow.build(),),
            timeout_seconds=30
        )
    """
    kwargs = kwargs or {}

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout_seconds)
            logger.info(
                f"Workflow completed successfully | function={func.__name__} | timeout={timeout_seconds}s"
            )
            return result
        except FuturesTimeoutError:
            error_msg = f"Workflow execution exceeded timeout of {timeout_seconds}s"
            logger.error(
                f"{error_msg} | function={func.__name__}",
                extra={
                    "timeout_seconds": timeout_seconds,
                    "function": func.__name__
                }
            )
            raise WorkflowTimeoutError(error_msg)
        except Exception as e:
            logger.error(
                f"Workflow execution failed | function={func.__name__} | error={str(e)}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__
                }
            )
            raise
