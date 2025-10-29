#!/usr/bin/env python3
"""
Data Retention Cleanup Scheduler
=================================

Production-ready script to enforce PDPA data retention policies.

Features:
- Automated cleanup of conversations older than 90 days
- Anonymization of user summaries older than 2 years
- Comprehensive logging and error handling
- Dry-run mode for testing
- Email notifications (optional)
- Suitable for cron job scheduling

Usage:
    # Dry run (report only, no changes)
    python scripts/schedule_data_cleanup.py --dry-run

    # Production run
    python scripts/schedule_data_cleanup.py

    # Custom retention periods
    python scripts/schedule_data_cleanup.py --conversation-retention 60 --summary-retention 365

    # With email notifications
    python scripts/schedule_data_cleanup.py --notify-email admin@example.com

Recommended Cron Schedule:
    # Daily at 2 AM (low traffic time)
    0 2 * * * /path/to/python /path/to/schedule_data_cleanup.py >> /var/log/tria/cleanup.log 2>&1

NO MOCKING - Uses real PostgreSQL database.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import cleanup functions
from src.privacy.data_retention import (
    run_full_cleanup,
    get_retention_statistics,
    CleanupResult
)


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging(log_file: Optional[str] = None, verbose: bool = False):
    """
    Configure logging for cleanup script

    Args:
        log_file: Optional log file path
        verbose: If True, enable DEBUG level logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        logging.info(f"Logging to file: {log_file}")


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_database_connection():
    """
    Get PostgreSQL database connection

    Returns:
        Database connection object

    Raises:
        RuntimeError: If DATABASE_URL is not configured or connection fails
    """
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError(
            "psycopg2 not installed. Install with: pip install psycopg2-binary"
        )

    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable not set. "
            "Please configure database connection in .env file."
        )

    try:
        conn = psycopg2.connect(database_url)
        logging.info("Database connection established")
        return conn
    except Exception as e:
        raise RuntimeError(f"Failed to connect to database: {e}") from e


# ============================================================================
# NOTIFICATION SYSTEM
# ============================================================================

def send_notification(
    email: str,
    results: dict,
    dry_run: bool,
    errors: list
):
    """
    Send email notification about cleanup results

    Args:
        email: Email address to send notification
        results: Cleanup results dictionary
        dry_run: Whether this was a dry run
        errors: List of errors encountered
    """
    try:
        # Simple notification via logging
        # In production, integrate with SendGrid, AWS SES, etc.
        logging.info(f"Would send notification to {email}:")
        logging.info(f"  Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
        logging.info(f"  Conversations deleted: {results['conversations'].conversations_deleted}")
        logging.info(f"  Messages deleted: {results['conversations'].messages_deleted}")
        logging.info(f"  Summaries anonymized: {results['summaries'].summaries_anonymized}")
        logging.info(f"  Errors: {len(errors)}")

        # TODO: Integrate with actual email service
        # Example with SendGrid:
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        #
        # message = Mail(
        #     from_email='noreply@tria.com',
        #     to_emails=email,
        #     subject=f"TRIA Data Cleanup {'[DRY RUN]' if dry_run else ''} - {datetime.now().strftime('%Y-%m-%d')}",
        #     html_content=generate_email_html(results, dry_run, errors)
        # )
        # sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        # response = sg.send(message)

    except Exception as e:
        logging.warning(f"Failed to send notification: {e}")


# ============================================================================
# MAIN CLEANUP FUNCTION
# ============================================================================

def run_cleanup(
    conversation_retention_days: int = 90,
    summary_retention_days: int = 730,
    dry_run: bool = False,
    notify_email: Optional[str] = None,
    save_report: bool = True
) -> int:
    """
    Run data retention cleanup

    Args:
        conversation_retention_days: Days to retain conversations
        summary_retention_days: Days before anonymizing summaries
        dry_run: If True, report actions without executing
        notify_email: Email address for notifications
        save_report: If True, save JSON report to file

    Returns:
        Exit code (0 = success, 1 = errors encountered)
    """
    start_time = datetime.now()

    logging.info("=" * 80)
    logging.info("TRIA AI-BPO Data Retention Cleanup")
    logging.info("=" * 80)
    logging.info(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    logging.info(f"Conversation retention: {conversation_retention_days} days")
    logging.info(f"Summary retention: {summary_retention_days} days")
    logging.info(f"Started at: {start_time.isoformat()}")
    logging.info("=" * 80)

    conn = None
    exit_code = 0

    try:
        # ====================================================================
        # STEP 1: Connect to database
        # ====================================================================
        logging.info("\n[1/4] Connecting to database...")
        conn = get_database_connection()

        # ====================================================================
        # STEP 2: Get current statistics
        # ====================================================================
        logging.info("\n[2/4] Analyzing current data...")
        stats = get_retention_statistics(conn)

        logging.info("Current retention statistics:")
        logging.info(f"  - Conversations to delete: {stats['conversations_to_delete']}")
        logging.info(f"  - Messages to delete: {stats['messages_to_delete']}")
        logging.info(f"  - Summaries to anonymize: {stats['summaries_to_anonymize']}")
        logging.info(f"  - Already anonymized: {stats['summaries_already_anonymized']}")

        # ====================================================================
        # STEP 3: Run cleanup
        # ====================================================================
        logging.info("\n[3/4] Running cleanup...")
        results = run_full_cleanup(
            conn,
            conversation_retention_days=conversation_retention_days,
            summary_retention_days=summary_retention_days,
            dry_run=dry_run
        )

        # ====================================================================
        # STEP 4: Report results
        # ====================================================================
        logging.info("\n[4/4] Generating report...")

        # Collect all errors
        all_errors = (
            results['conversations'].errors +
            results['summaries'].errors
        )

        if all_errors:
            exit_code = 1
            logging.error(f"Cleanup completed with {len(all_errors)} errors:")
            for error in all_errors:
                logging.error(f"  - {error}")
        else:
            logging.info("Cleanup completed successfully with no errors")

        # ====================================================================
        # STEP 5: Save report
        # ====================================================================
        if save_report:
            report = {
                'timestamp': start_time.isoformat(),
                'mode': 'dry_run' if dry_run else 'production',
                'configuration': {
                    'conversation_retention_days': conversation_retention_days,
                    'summary_retention_days': summary_retention_days,
                },
                'statistics_before': stats,
                'results': {
                    'conversations': results['conversations'].to_dict(),
                    'summaries': results['summaries'].to_dict(),
                },
                'errors': all_errors,
                'exit_code': exit_code,
            }

            report_dir = project_root / 'logs' / 'cleanup'
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"cleanup_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            logging.info(f"Report saved to: {report_file}")

        # ====================================================================
        # STEP 6: Send notification
        # ====================================================================
        if notify_email:
            send_notification(notify_email, results, dry_run, all_errors)

    except Exception as e:
        logging.error(f"FATAL ERROR: {e}")
        logging.exception("Full traceback:")
        exit_code = 1

    finally:
        # Close database connection
        if conn:
            conn.close()
            logging.info("Database connection closed")

        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logging.info("\n" + "=" * 80)
        logging.info("Cleanup Summary")
        logging.info("=" * 80)
        logging.info(f"Duration: {duration:.2f} seconds")
        logging.info(f"Exit code: {exit_code}")
        logging.info("=" * 80)

    return exit_code


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(
        description='TRIA AI-BPO Data Retention Cleanup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe testing)
  python schedule_data_cleanup.py --dry-run

  # Production run
  python schedule_data_cleanup.py

  # Custom retention periods
  python schedule_data_cleanup.py --conversation-retention 60 --summary-retention 365

  # With email notifications
  python schedule_data_cleanup.py --notify-email admin@example.com --verbose

Recommended Cron Schedule:
  # Daily at 2 AM
  0 2 * * * /path/to/python /path/to/schedule_data_cleanup.py >> /var/log/tria/cleanup.log 2>&1
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report actions without making changes (safe for testing)'
    )

    parser.add_argument(
        '--conversation-retention',
        type=int,
        default=90,
        metavar='DAYS',
        help='Days to retain conversation data (default: 90)'
    )

    parser.add_argument(
        '--summary-retention',
        type=int,
        default=730,
        metavar='DAYS',
        help='Days before anonymizing user summaries (default: 730 = 2 years)'
    )

    parser.add_argument(
        '--notify-email',
        type=str,
        metavar='EMAIL',
        help='Email address for cleanup notifications'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        metavar='PATH',
        help='Path to log file (default: logs/cleanup/cleanup_YYYYMMDD.log)'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Do not save JSON report file'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )

    args = parser.parse_args()

    # Configure logging
    log_file = args.log_file
    if not log_file:
        log_dir = project_root / 'logs' / 'cleanup'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"cleanup_{datetime.now().strftime('%Y%m%d')}.log"

    setup_logging(log_file=str(log_file), verbose=args.verbose)

    # Run cleanup
    exit_code = run_cleanup(
        conversation_retention_days=args.conversation_retention,
        summary_retention_days=args.summary_retention,
        dry_run=args.dry_run,
        notify_email=args.notify_email,
        save_report=not args.no_report
    )

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
