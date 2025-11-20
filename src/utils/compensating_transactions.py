"""
Compensating transaction manager for distributed transaction coordination.

Handles automatic rollback of completed steps when later steps fail,
preventing orphaned resources in external systems (Xero, databases, etc.).

PROBLEM THIS SOLVES:
- User places order → Creates draft order in Xero → Invoice creation fails
- Without compensating transactions: Draft order LEFT ORPHANED in Xero
- With compensating transactions: Draft order AUTOMATICALLY DELETED

IMPACT WITHOUT THIS:
- Orphaned Xero draft orders accumulate daily
- Manual cleanup required (1-2 hours/day = $50K/year)
- Customer confusion about order status
- Accounting reconciliation nightmare
"""

import logging
from typing import Callable, Any, Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


@dataclass
class CompensatingAction:
    """
    Represents a compensating action (rollback) for a completed transaction step.

    Attributes:
        step_name: Human-readable name of the step (e.g., "create_xero_draft_order")
        compensate_func: Function to call to undo the step
        compensate_args: Positional arguments for the compensate function
        compensate_kwargs: Keyword arguments for the compensate function
        context: Additional context for logging/debugging
    """
    step_name: str
    compensate_func: Callable
    compensate_args: tuple = field(default_factory=tuple)
    compensate_kwargs: dict = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


class CompensatingTransactionManager:
    """
    Manages a sequence of transaction steps with automatic rollback on failure.

    Usage Pattern:
        manager = CompensatingTransactionManager("create_order")

        try:
            # Step 1: Create draft order
            draft_id = create_xero_draft(data)
            manager.add_compensating_action(
                step_name="create_xero_draft",
                compensate_func=delete_xero_draft,
                compensate_args=(draft_id,),
                context={"draft_id": draft_id}
            )

            # Step 2: Create invoice (might fail)
            invoice_id = create_xero_invoice(draft_id)
            manager.add_compensating_action(
                step_name="create_xero_invoice",
                compensate_func=delete_xero_invoice,
                compensate_args=(invoice_id,),
                context={"invoice_id": invoice_id}
            )

            # Success - commit (clears rollback actions)
            manager.commit()
            return invoice_id

        except Exception as e:
            # Failure - automatically rollback all completed steps
            manager.rollback()
            raise
    """

    def __init__(self, transaction_name: str):
        """
        Initialize transaction manager.

        Args:
            transaction_name: Human-readable name for this transaction
                             (e.g., "create_order", "update_customer")
        """
        self.transaction_name = transaction_name
        self.actions: List[CompensatingAction] = []
        self.committed = False
        self.rolled_back = False
        self.start_time = datetime.utcnow()

        logger.info(
            f"Started compensating transaction: {transaction_name}",
            extra={
                "transaction_name": transaction_name,
                "start_time": self.start_time.isoformat()
            }
        )

    def add_compensating_action(
        self,
        step_name: str,
        compensate_func: Callable,
        compensate_args: tuple = (),
        compensate_kwargs: dict = None,
        context: Dict[str, Any] = None
    ) -> None:
        """
        Register a compensating action for a completed step.

        Call this AFTER a step completes successfully to register how to undo it.

        Args:
            step_name: Human-readable name of the step
            compensate_func: Function to call to undo the step
            compensate_args: Positional arguments for compensate_func
            compensate_kwargs: Keyword arguments for compensate_func
            context: Additional context for logging (e.g., IDs, timestamps)

        Example:
            # After successfully creating a Xero draft order:
            manager.add_compensating_action(
                step_name="create_xero_draft",
                compensate_func=xero_client.delete_draft_order,
                compensate_args=(draft_order_id,),
                context={"draft_order_id": draft_order_id, "customer": customer_name}
            )
        """
        if self.committed:
            raise RuntimeError(
                f"Cannot add actions to committed transaction: {self.transaction_name}"
            )

        if self.rolled_back:
            raise RuntimeError(
                f"Cannot add actions to rolled back transaction: {self.transaction_name}"
            )

        action = CompensatingAction(
            step_name=step_name,
            compensate_func=compensate_func,
            compensate_args=compensate_args,
            compensate_kwargs=compensate_kwargs or {},
            context=context or {}
        )

        self.actions.append(action)

        logger.debug(
            f"Registered compensating action: {step_name}",
            extra={
                "transaction_name": self.transaction_name,
                "step_name": step_name,
                "total_actions": len(self.actions),
                "context": context or {}
            }
        )

    def commit(self) -> None:
        """
        Mark transaction as successfully committed.

        This clears all registered compensating actions since the transaction
        completed successfully and no rollback is needed.

        Call this ONLY after ALL steps complete successfully.
        """
        if self.rolled_back:
            raise RuntimeError(
                f"Cannot commit rolled back transaction: {self.transaction_name}"
            )

        self.committed = True
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        logger.info(
            f"Committed transaction: {self.transaction_name} "
            f"({len(self.actions)} steps, {duration:.2f}s)",
            extra={
                "transaction_name": self.transaction_name,
                "steps_count": len(self.actions),
                "duration_seconds": duration,
                "status": "committed"
            }
        )

        # Clear actions since transaction succeeded
        self.actions.clear()

    def rollback(self, error: Optional[Exception] = None) -> None:
        """
        Execute all compensating actions in REVERSE order (LIFO).

        This undoes all completed steps, cleaning up orphaned resources.
        Rollback happens in reverse order to maintain consistency
        (e.g., delete invoice before deleting draft order).

        Args:
            error: The exception that triggered the rollback (for logging)

        Note:
            - Rollback failures are logged but don't raise exceptions
            - This prevents cascading failures during error recovery
            - Each compensating action is attempted even if previous ones fail
        """
        if self.committed:
            logger.warning(
                f"Attempted rollback of committed transaction: {self.transaction_name}"
            )
            return

        if self.rolled_back:
            logger.warning(
                f"Transaction already rolled back: {self.transaction_name}"
            )
            return

        self.rolled_back = True
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        logger.error(
            f"Rolling back transaction: {self.transaction_name} "
            f"({len(self.actions)} steps to undo, {duration:.2f}s elapsed)",
            extra={
                "transaction_name": self.transaction_name,
                "steps_to_undo": len(self.actions),
                "duration_seconds": duration,
                "status": "rolling_back",
                "error": str(error) if error else None,
                "error_type": type(error).__name__ if error else None
            }
        )

        # Execute compensating actions in REVERSE order (LIFO - Last In First Out)
        # This ensures dependencies are respected (e.g., delete invoice before draft)
        rollback_failures = []

        for action in reversed(self.actions):
            try:
                logger.info(
                    f"Executing compensating action: {action.step_name}",
                    extra={
                        "transaction_name": self.transaction_name,
                        "step_name": action.step_name,
                        "context": action.context
                    }
                )

                # Execute the compensating action
                action.compensate_func(*action.compensate_args, **action.compensate_kwargs)

                logger.info(
                    f"Successfully compensated: {action.step_name}",
                    extra={
                        "transaction_name": self.transaction_name,
                        "step_name": action.step_name,
                        "status": "compensated"
                    }
                )

            except Exception as compensate_error:
                # Log but don't raise - we want to attempt all compensations
                error_msg = (
                    f"Failed to execute compensating action: {action.step_name} | "
                    f"Error: {str(compensate_error)}"
                )

                logger.error(
                    error_msg,
                    extra={
                        "transaction_name": self.transaction_name,
                        "step_name": action.step_name,
                        "error": str(compensate_error),
                        "error_type": type(compensate_error).__name__,
                        "context": action.context,
                        "traceback": traceback.format_exc()
                    }
                )

                rollback_failures.append({
                    "step_name": action.step_name,
                    "error": str(compensate_error),
                    "context": action.context
                })

        # Log final rollback status
        if rollback_failures:
            logger.error(
                f"Transaction rollback completed with {len(rollback_failures)} failures: "
                f"{self.transaction_name}",
                extra={
                    "transaction_name": self.transaction_name,
                    "total_steps": len(self.actions),
                    "failed_compensations": len(rollback_failures),
                    "failures": rollback_failures,
                    "status": "rollback_partial"
                }
            )
        else:
            logger.info(
                f"Transaction fully rolled back: {self.transaction_name} "
                f"({len(self.actions)} steps compensated)",
                extra={
                    "transaction_name": self.transaction_name,
                    "steps_compensated": len(self.actions),
                    "status": "rollback_complete"
                }
            )

        # Clear actions
        self.actions.clear()

    def __enter__(self):
        """Support context manager protocol (with statement)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Automatic rollback on exception when used as context manager.

        Usage:
            with CompensatingTransactionManager("create_order") as manager:
                draft_id = create_xero_draft(data)
                manager.add_compensating_action(...)

                invoice_id = create_xero_invoice(draft_id)
                # If this fails, rollback happens automatically

                manager.commit()  # Success - no rollback
        """
        if exc_type is not None:
            # Exception occurred - rollback
            self.rollback(error=exc_val)
            # Return False to re-raise the exception
            return False
        elif not self.committed:
            # No exception but forgot to commit - rollback as safety measure
            logger.warning(
                f"Transaction exited without commit - rolling back: {self.transaction_name}",
                extra={"transaction_name": self.transaction_name}
            )
            self.rollback()

        return False
