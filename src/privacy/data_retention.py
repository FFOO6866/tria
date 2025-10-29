"""
PDPA-Compliant Data Retention and Cleanup
==========================================

Production-ready data retention policy enforcement for TRIA AI-BPO.

Features:
- Automatic cleanup of conversations older than 90 days
- Anonymization of user summaries older than 2 years
- Audit logging of all cleanup actions
- Dry-run mode for testing

NO MOCKING - Uses real PostgreSQL database with transactions.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """
    Results from cleanup operations

    Attributes:
        conversations_deleted: Number of conversation sessions deleted
        messages_deleted: Number of individual messages deleted
        summaries_anonymized: Number of user summaries anonymized
        errors: List of error messages encountered
        dry_run: Whether this was a dry run
        started_at: When cleanup started
        completed_at: When cleanup completed
    """
    conversations_deleted: int = 0
    messages_deleted: int = 0
    summaries_anonymized: int = 0
    errors: list = field(default_factory=list)
    dry_run: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'conversations_deleted': self.conversations_deleted,
            'messages_deleted': self.messages_deleted,
            'summaries_anonymized': self.summaries_anonymized,
            'errors': self.errors,
            'dry_run': self.dry_run,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            ),
        }


# ============================================================================
# CONVERSATION DATA CLEANUP (90-DAY RETENTION)
# ============================================================================

def cleanup_old_conversations(
    db_connection,
    retention_days: int = 90,
    dry_run: bool = False,
    batch_size: int = 1000
) -> CleanupResult:
    """
    Delete conversation data older than retention period

    Implements PDPA requirement: Conversation messages retained for 90 days only.

    Process:
    1. Find conversation sessions older than retention period
    2. Delete associated messages (in batches for performance)
    3. Delete conversation sessions
    4. Log all deletions for audit trail

    Args:
        db_connection: PostgreSQL database connection (psycopg2 or SQLAlchemy)
        retention_days: Number of days to retain conversations (default: 90)
        dry_run: If True, report what would be deleted without deleting
        batch_size: Number of records to delete per batch

    Returns:
        CleanupResult with deletion statistics

    Example:
        >>> import psycopg2
        >>> conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        >>> result = cleanup_old_conversations(conn, retention_days=90, dry_run=True)
        >>> print(f"Would delete {result.conversations_deleted} conversations")
    """
    result = CleanupResult(
        dry_run=dry_run,
        started_at=datetime.utcnow()
    )

    try:
        cursor = db_connection.cursor()

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Starting conversation cleanup "
            f"(retention: {retention_days} days, cutoff: {cutoff_date.isoformat()})"
        )

        # ====================================================================
        # STEP 1: Find conversations to delete
        # ====================================================================
        cursor.execute("""
            SELECT session_id, end_time
            FROM conversation_sessions
            WHERE end_time < %s
            OR (end_time IS NULL AND start_time < %s)
            ORDER BY end_time ASC
        """, (cutoff_date, cutoff_date))

        sessions_to_delete = cursor.fetchall()
        result.conversations_deleted = len(sessions_to_delete)

        if result.conversations_deleted == 0:
            logger.info("No conversations found for cleanup")
            result.completed_at = datetime.utcnow()
            return result

        logger.info(f"Found {result.conversations_deleted} conversations to delete")

        # ====================================================================
        # STEP 2: Count and delete messages (in batches)
        # ====================================================================
        session_ids = [session[0] for session in sessions_to_delete]

        # Count messages to be deleted
        cursor.execute("""
            SELECT COUNT(*)
            FROM conversation_messages
            WHERE session_id = ANY(%s)
        """, (session_ids,))

        result.messages_deleted = cursor.fetchone()[0]
        logger.info(f"Found {result.messages_deleted} messages to delete")

        if not dry_run:
            # Delete messages in batches to avoid long-running transactions
            for i in range(0, len(session_ids), batch_size):
                batch = session_ids[i:i + batch_size]
                cursor.execute("""
                    DELETE FROM conversation_messages
                    WHERE session_id = ANY(%s)
                """, (batch,))

                deleted = cursor.rowcount
                logger.debug(f"Deleted batch of {deleted} messages")

            # Commit message deletions
            db_connection.commit()
            logger.info(f"Deleted {result.messages_deleted} messages")

        # ====================================================================
        # STEP 3: Delete conversation sessions
        # ====================================================================
        if not dry_run:
            cursor.execute("""
                DELETE FROM conversation_sessions
                WHERE session_id = ANY(%s)
            """, (session_ids,))

            db_connection.commit()
            logger.info(f"Deleted {result.conversations_deleted} conversation sessions")

        # ====================================================================
        # STEP 4: Log audit trail
        # ====================================================================
        audit_log = {
            'action': 'cleanup_old_conversations',
            'dry_run': dry_run,
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.isoformat(),
            'conversations_deleted': result.conversations_deleted,
            'messages_deleted': result.messages_deleted,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if not dry_run:
            _log_cleanup_action(cursor, audit_log)
            db_connection.commit()

        logger.info(
            f"{'[DRY RUN] Would delete' if dry_run else 'Deleted'} "
            f"{result.conversations_deleted} conversations "
            f"({result.messages_deleted} messages)"
        )

    except Exception as e:
        error_msg = f"Error during conversation cleanup: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)

        if not dry_run:
            db_connection.rollback()

    finally:
        result.completed_at = datetime.utcnow()

    return result


# ============================================================================
# USER SUMMARY ANONYMIZATION (2-YEAR RETENTION)
# ============================================================================

def anonymize_old_summaries(
    db_connection,
    retention_days: int = 730,  # 2 years
    dry_run: bool = False
) -> CleanupResult:
    """
    Anonymize user interaction summaries older than retention period

    Implements PDPA requirement: User summaries retained for 2 years,
    then anonymized while preserving analytics value.

    Anonymization process:
    - Replace user_id with hash: ANON_<hash>
    - Preserve aggregated statistics (counts, preferences, etc.)
    - Mark as anonymized to prevent re-processing

    Args:
        db_connection: PostgreSQL database connection
        retention_days: Number of days before anonymization (default: 730 = 2 years)
        dry_run: If True, report what would be anonymized without changing data

    Returns:
        CleanupResult with anonymization statistics

    Example:
        >>> result = anonymize_old_summaries(conn, retention_days=730, dry_run=True)
        >>> print(f"Would anonymize {result.summaries_anonymized} user summaries")
    """
    result = CleanupResult(
        dry_run=dry_run,
        started_at=datetime.utcnow()
    )

    try:
        cursor = db_connection.cursor()

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        logger.info(
            f"{'[DRY RUN] ' if dry_run else ''}Starting user summary anonymization "
            f"(retention: {retention_days} days, cutoff: {cutoff_date.isoformat()})"
        )

        # ====================================================================
        # STEP 1: Find summaries to anonymize
        # ====================================================================
        # Only anonymize summaries that haven't been anonymized yet
        cursor.execute("""
            SELECT user_id, created_at, last_interaction
            FROM user_interaction_summaries
            WHERE created_at < %s
            AND user_id NOT LIKE 'ANON_%%'
            ORDER BY created_at ASC
        """, (cutoff_date,))

        summaries_to_anonymize = cursor.fetchall()
        result.summaries_anonymized = len(summaries_to_anonymize)

        if result.summaries_anonymized == 0:
            logger.info("No user summaries found for anonymization")
            result.completed_at = datetime.utcnow()
            return result

        logger.info(f"Found {result.summaries_anonymized} user summaries to anonymize")

        # ====================================================================
        # STEP 2: Anonymize user IDs
        # ====================================================================
        if not dry_run:
            for user_id, created_at, last_interaction in summaries_to_anonymize:
                # Generate deterministic anonymous ID (hash of user_id)
                anon_id = _generate_anonymous_id(user_id)

                cursor.execute("""
                    UPDATE user_interaction_summaries
                    SET user_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (anon_id, user_id))

                logger.debug(f"Anonymized user {user_id[:8]}... -> {anon_id}")

            # Commit anonymization
            db_connection.commit()
            logger.info(f"Anonymized {result.summaries_anonymized} user summaries")

        # ====================================================================
        # STEP 3: Log audit trail
        # ====================================================================
        audit_log = {
            'action': 'anonymize_old_summaries',
            'dry_run': dry_run,
            'retention_days': retention_days,
            'cutoff_date': cutoff_date.isoformat(),
            'summaries_anonymized': result.summaries_anonymized,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if not dry_run:
            _log_cleanup_action(cursor, audit_log)
            db_connection.commit()

        logger.info(
            f"{'[DRY RUN] Would anonymize' if dry_run else 'Anonymized'} "
            f"{result.summaries_anonymized} user summaries"
        )

    except Exception as e:
        error_msg = f"Error during user summary anonymization: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)

        if not dry_run:
            db_connection.rollback()

    finally:
        result.completed_at = datetime.utcnow()

    return result


# ============================================================================
# COMBINED CLEANUP OPERATION
# ============================================================================

def run_full_cleanup(
    db_connection,
    conversation_retention_days: int = 90,
    summary_retention_days: int = 730,
    dry_run: bool = False
) -> Dict[str, CleanupResult]:
    """
    Run complete data retention cleanup

    Executes both conversation cleanup and user summary anonymization
    in a single operation with comprehensive logging.

    Args:
        db_connection: PostgreSQL database connection
        conversation_retention_days: Days to retain conversations (default: 90)
        summary_retention_days: Days before anonymizing summaries (default: 730)
        dry_run: If True, report actions without executing

    Returns:
        Dictionary with 'conversations' and 'summaries' CleanupResult objects

    Example:
        >>> results = run_full_cleanup(conn, dry_run=True)
        >>> print(f"Total deletions: {results['conversations'].messages_deleted}")
        >>> print(f"Total anonymizations: {results['summaries'].summaries_anonymized}")
    """
    logger.info("=" * 80)
    logger.info(
        f"Starting full data retention cleanup "
        f"({'DRY RUN' if dry_run else 'PRODUCTION MODE'})"
    )
    logger.info("=" * 80)

    results = {}

    # Run conversation cleanup
    logger.info("\n[1/2] Cleaning up old conversations...")
    results['conversations'] = cleanup_old_conversations(
        db_connection,
        retention_days=conversation_retention_days,
        dry_run=dry_run
    )

    # Run user summary anonymization
    logger.info("\n[2/2] Anonymizing old user summaries...")
    results['summaries'] = anonymize_old_summaries(
        db_connection,
        retention_days=summary_retention_days,
        dry_run=dry_run
    )

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("Data Retention Cleanup Summary")
    logger.info("=" * 80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    logger.info(f"\nConversations:")
    logger.info(f"  - Sessions deleted: {results['conversations'].conversations_deleted}")
    logger.info(f"  - Messages deleted: {results['conversations'].messages_deleted}")
    logger.info(f"\nUser Summaries:")
    logger.info(f"  - Summaries anonymized: {results['summaries'].summaries_anonymized}")
    logger.info(f"\nErrors:")
    all_errors = results['conversations'].errors + results['summaries'].errors
    if all_errors:
        for error in all_errors:
            logger.info(f"  - {error}")
    else:
        logger.info("  - None")
    logger.info("=" * 80)

    return results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _generate_anonymous_id(user_id: str) -> str:
    """
    Generate deterministic anonymous ID from user ID

    Uses SHA-256 hash to create irreversible but consistent anonymous ID.
    Format: ANON_<first 32 chars of hash>

    Args:
        user_id: Original user ID

    Returns:
        Anonymous ID string
    """
    # Hash user ID with SHA-256
    hash_object = hashlib.sha256(user_id.encode('utf-8'))
    hash_hex = hash_object.hexdigest()

    # Return ANON prefix + first 32 chars of hash
    return f"ANON_{hash_hex[:32]}"


def _log_cleanup_action(cursor, audit_log: dict):
    """
    Log cleanup action to audit trail

    Creates/updates audit_log table to track all data retention actions
    for PDPA compliance verification.

    Args:
        cursor: Database cursor
        audit_log: Dictionary of audit information
    """
    try:
        # Ensure audit_log table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_retention_audit_log (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                details JSONB NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert audit log entry
        cursor.execute("""
            INSERT INTO data_retention_audit_log (action, details)
            VALUES (%s, %s)
        """, (audit_log['action'], str(audit_log)))

        logger.debug(f"Logged audit trail for {audit_log['action']}")

    except Exception as e:
        logger.warning(f"Failed to log audit trail: {e}")


def get_retention_statistics(db_connection) -> Dict[str, Any]:
    """
    Get current retention statistics

    Returns statistics about data eligible for cleanup/anonymization.
    Useful for monitoring and planning cleanup operations.

    Args:
        db_connection: PostgreSQL database connection

    Returns:
        Dictionary with retention statistics

    Example:
        >>> stats = get_retention_statistics(conn)
        >>> print(f"Conversations due for deletion: {stats['conversations_to_delete']}")
    """
    cursor = db_connection.cursor()

    cutoff_90_days = datetime.utcnow() - timedelta(days=90)
    cutoff_730_days = datetime.utcnow() - timedelta(days=730)

    stats = {}

    # Count conversations due for deletion
    cursor.execute("""
        SELECT COUNT(*)
        FROM conversation_sessions
        WHERE end_time < %s
        OR (end_time IS NULL AND start_time < %s)
    """, (cutoff_90_days, cutoff_90_days))
    stats['conversations_to_delete'] = cursor.fetchone()[0]

    # Count messages in those conversations
    cursor.execute("""
        SELECT COUNT(*)
        FROM conversation_messages cm
        WHERE EXISTS (
            SELECT 1 FROM conversation_sessions cs
            WHERE cs.session_id = cm.session_id
            AND (cs.end_time < %s OR (cs.end_time IS NULL AND cs.start_time < %s))
        )
    """, (cutoff_90_days, cutoff_90_days))
    stats['messages_to_delete'] = cursor.fetchone()[0]

    # Count summaries due for anonymization
    cursor.execute("""
        SELECT COUNT(*)
        FROM user_interaction_summaries
        WHERE created_at < %s
        AND user_id NOT LIKE 'ANON_%%'
    """, (cutoff_730_days,))
    stats['summaries_to_anonymize'] = cursor.fetchone()[0]

    # Count already anonymized summaries
    cursor.execute("""
        SELECT COUNT(*)
        FROM user_interaction_summaries
        WHERE user_id LIKE 'ANON_%%'
    """, ())
    stats['summaries_already_anonymized'] = cursor.fetchone()[0]

    return stats


if __name__ == "__main__":
    """Test retention policies with dry run"""
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Connect to database
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        exit(1)

    conn = psycopg2.connect(db_url)

    try:
        # Get current statistics
        print("\nCurrent Retention Statistics:")
        print("=" * 80)
        stats = get_retention_statistics(conn)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("=" * 80)

        # Run dry-run cleanup
        print("\nRunning dry-run cleanup...")
        results = run_full_cleanup(conn, dry_run=True)

    finally:
        conn.close()
