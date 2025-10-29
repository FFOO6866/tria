"""
Data Retention Integration Tests
=================================

Integration tests for PDPA-compliant data retention policies.
Uses REAL PostgreSQL database - NO MOCKING.

Tests:
- Conversation cleanup (90-day retention)
- User summary anonymization (2-year retention)
- Audit logging
- Statistics reporting

Prerequisites:
- PostgreSQL database configured in DATABASE_URL
- Test data loaded via fixtures
"""

import pytest
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2

from src.privacy.data_retention import (
    cleanup_old_conversations,
    anonymize_old_summaries,
    run_full_cleanup,
    get_retention_statistics,
    _generate_anonymous_id,
)

# Load environment variables
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / '.env')


@pytest.fixture(scope="module")
def db_connection():
    """
    Provide PostgreSQL database connection for tests

    NO MOCKING - Uses real database from DATABASE_URL
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        pytest.skip("DATABASE_URL not configured")

    conn = psycopg2.connect(database_url)
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def clean_test_data(db_connection):
    """
    Clean up test data before and after each test

    Ensures tests start with clean state
    """
    cursor = db_connection.cursor()

    # Clean up before test
    cursor.execute("DELETE FROM conversation_messages WHERE session_id LIKE 'test_%'")
    cursor.execute("DELETE FROM conversation_sessions WHERE session_id LIKE 'test_%'")
    cursor.execute("DELETE FROM user_interaction_summaries WHERE user_id LIKE 'test_%'")
    cursor.execute("DELETE FROM data_retention_audit_log WHERE details::text LIKE '%test_%'")
    db_connection.commit()

    yield

    # Clean up after test
    cursor.execute("DELETE FROM conversation_messages WHERE session_id LIKE 'test_%'")
    cursor.execute("DELETE FROM conversation_sessions WHERE session_id LIKE 'test_%'")
    cursor.execute("DELETE FROM user_interaction_summaries WHERE user_id LIKE 'test_%'")
    cursor.execute("DELETE FROM data_retention_audit_log WHERE details::text LIKE '%test_%'")
    db_connection.commit()


class TestConversationCleanup:
    """Test conversation data cleanup (90-day retention)"""

    def test_cleanup_old_conversations_dry_run(self, db_connection, clean_test_data):
        """Test dry run mode reports without deleting"""
        cursor = db_connection.cursor()

        # Create old conversation (100 days ago)
        old_date = datetime.utcnow() - timedelta(days=100)
        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_old_session', 'test_user', %s, %s, 2, %s)
        """, (old_date, old_date, old_date))

        # Add messages
        cursor.execute("""
            INSERT INTO conversation_messages
            (session_id, role, content, timestamp, created_at)
            VALUES
            ('test_old_session', 'user', 'Hello', %s, %s),
            ('test_old_session', 'assistant', 'Hi', %s, %s)
        """, (old_date, old_date, old_date, old_date))

        db_connection.commit()

        # Run cleanup in dry-run mode
        result = cleanup_old_conversations(db_connection, retention_days=90, dry_run=True)

        # Verify reporting
        assert result.dry_run is True
        assert result.conversations_deleted >= 1
        assert result.messages_deleted >= 2

        # Verify data NOT deleted
        cursor.execute("SELECT COUNT(*) FROM conversation_sessions WHERE session_id = 'test_old_session'")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE session_id = 'test_old_session'")
        assert cursor.fetchone()[0] == 2

    def test_cleanup_deletes_old_conversations(self, db_connection, clean_test_data):
        """Test actual deletion of old conversations"""
        cursor = db_connection.cursor()

        # Create old conversation (100 days ago)
        old_date = datetime.utcnow() - timedelta(days=100)
        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_old_session', 'test_user', %s, %s, 2, %s)
        """, (old_date, old_date, old_date))

        cursor.execute("""
            INSERT INTO conversation_messages
            (session_id, role, content, timestamp, created_at)
            VALUES
            ('test_old_session', 'user', 'Hello', %s, %s),
            ('test_old_session', 'assistant', 'Hi', %s, %s)
        """, (old_date, old_date, old_date, old_date))

        db_connection.commit()

        # Run cleanup
        result = cleanup_old_conversations(db_connection, retention_days=90, dry_run=False)

        # Verify deletion
        assert result.conversations_deleted >= 1
        assert result.messages_deleted >= 2

        cursor.execute("SELECT COUNT(*) FROM conversation_sessions WHERE session_id = 'test_old_session'")
        assert cursor.fetchone()[0] == 0

        cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE session_id = 'test_old_session'")
        assert cursor.fetchone()[0] == 0

    def test_cleanup_preserves_recent_conversations(self, db_connection, clean_test_data):
        """Test that recent conversations are NOT deleted"""
        cursor = db_connection.cursor()

        # Create recent conversation (30 days ago)
        recent_date = datetime.utcnow() - timedelta(days=30)
        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_recent_session', 'test_user', %s, %s, 1, %s)
        """, (recent_date, recent_date, recent_date))

        cursor.execute("""
            INSERT INTO conversation_messages
            (session_id, role, content, timestamp, created_at)
            VALUES ('test_recent_session', 'user', 'Hello', %s, %s)
        """, (recent_date, recent_date))

        db_connection.commit()

        # Run cleanup
        cleanup_old_conversations(db_connection, retention_days=90, dry_run=False)

        # Verify data preserved
        cursor.execute("SELECT COUNT(*) FROM conversation_sessions WHERE session_id = 'test_recent_session'")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM conversation_messages WHERE session_id = 'test_recent_session'")
        assert cursor.fetchone()[0] == 1


class TestUserSummaryAnonymization:
    """Test user summary anonymization (2-year retention)"""

    def test_anonymize_old_summaries_dry_run(self, db_connection, clean_test_data):
        """Test dry run mode reports without anonymizing"""
        cursor = db_connection.cursor()

        # Create old summary (3 years ago)
        old_date = datetime.utcnow() - timedelta(days=1100)
        cursor.execute("""
            INSERT INTO user_interaction_summaries
            (user_id, total_conversations, total_messages, preferred_language,
             last_interaction, created_at)
            VALUES ('test_old_user', 5, 20, 'en', %s, %s)
        """, (old_date, old_date))

        db_connection.commit()

        # Run anonymization in dry-run mode
        result = anonymize_old_summaries(db_connection, retention_days=730, dry_run=True)

        # Verify reporting
        assert result.dry_run is True
        assert result.summaries_anonymized >= 1

        # Verify data NOT anonymized
        cursor.execute("SELECT user_id FROM user_interaction_summaries WHERE user_id = 'test_old_user'")
        assert cursor.fetchone() is not None

    def test_anonymize_replaces_user_id(self, db_connection, clean_test_data):
        """Test that user IDs are replaced with anonymous hash"""
        cursor = db_connection.cursor()

        # Create old summary
        old_date = datetime.utcnow() - timedelta(days=1100)
        original_user_id = "test_old_user_123"

        cursor.execute("""
            INSERT INTO user_interaction_summaries
            (user_id, total_conversations, total_messages, preferred_language,
             last_interaction, created_at)
            VALUES (%s, 5, 20, 'en', %s, %s)
        """, (original_user_id, old_date, old_date))

        db_connection.commit()

        # Run anonymization
        result = anonymize_old_summaries(db_connection, retention_days=730, dry_run=False)

        # Verify anonymization
        assert result.summaries_anonymized >= 1

        cursor.execute("""
            SELECT user_id FROM user_interaction_summaries
            WHERE user_id LIKE 'ANON_%%'
        """)
        anon_row = cursor.fetchone()
        assert anon_row is not None

        anon_id = anon_row[0]
        assert anon_id.startswith('ANON_')

        # Verify it matches expected hash
        expected_anon_id = _generate_anonymous_id(original_user_id)
        assert anon_id == expected_anon_id

    def test_anonymize_preserves_statistics(self, db_connection, clean_test_data):
        """Test that anonymization preserves aggregate statistics"""
        cursor = db_connection.cursor()

        # Create old summary with data
        old_date = datetime.utcnow() - timedelta(days=1100)
        cursor.execute("""
            INSERT INTO user_interaction_summaries
            (user_id, total_conversations, total_messages, preferred_language,
             avg_satisfaction, last_interaction, created_at)
            VALUES ('test_stats_user', 10, 50, 'zh', 4.5, %s, %s)
        """, (old_date, old_date))

        db_connection.commit()

        # Run anonymization
        anonymize_old_summaries(db_connection, retention_days=730, dry_run=False)

        # Verify statistics preserved
        cursor.execute("""
            SELECT total_conversations, total_messages, preferred_language, avg_satisfaction
            FROM user_interaction_summaries
            WHERE user_id LIKE 'ANON_%%'
        """)
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 10  # total_conversations
        assert row[1] == 50  # total_messages
        assert row[2] == 'zh'  # preferred_language
        assert row[3] == 4.5  # avg_satisfaction

    def test_anonymize_doesnt_reanonymize(self, db_connection, clean_test_data):
        """Test that already anonymized summaries are not re-processed"""
        cursor = db_connection.cursor()

        # Create already-anonymized summary
        old_date = datetime.utcnow() - timedelta(days=1100)
        anon_id = _generate_anonymous_id("original_user")

        cursor.execute("""
            INSERT INTO user_interaction_summaries
            (user_id, total_conversations, total_messages, preferred_language,
             last_interaction, created_at)
            VALUES (%s, 5, 20, 'en', %s, %s)
        """, (anon_id, old_date, old_date))

        db_connection.commit()

        initial_count = cursor.execute("""
            SELECT COUNT(*) FROM user_interaction_summaries
            WHERE user_id LIKE 'ANON_%%'
        """)
        cursor.fetchone()

        # Run anonymization
        result = anonymize_old_summaries(db_connection, retention_days=730, dry_run=False)

        # Should not count already anonymized records
        assert result.summaries_anonymized == 0


class TestRetentionStatistics:
    """Test retention statistics reporting"""

    def test_get_retention_statistics(self, db_connection, clean_test_data):
        """Test statistics calculation"""
        cursor = db_connection.cursor()

        # Create test data
        old_date = datetime.utcnow() - timedelta(days=100)
        recent_date = datetime.utcnow() - timedelta(days=30)

        # Old conversation (should be counted)
        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_old_1', 'test_user', %s, %s, 1, %s)
        """, (old_date, old_date, old_date))

        cursor.execute("""
            INSERT INTO conversation_messages
            (session_id, role, content, timestamp, created_at)
            VALUES ('test_old_1', 'user', 'Test', %s, %s)
        """, (old_date, old_date))

        # Recent conversation (should NOT be counted)
        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_recent_1', 'test_user', %s, %s, 1, %s)
        """, (recent_date, recent_date, recent_date))

        db_connection.commit()

        # Get statistics
        stats = get_retention_statistics(db_connection)

        # Verify
        assert isinstance(stats, dict)
        assert 'conversations_to_delete' in stats
        assert 'messages_to_delete' in stats
        assert 'summaries_to_anonymize' in stats

        assert stats['conversations_to_delete'] >= 1
        assert stats['messages_to_delete'] >= 1


class TestFullCleanup:
    """Test combined cleanup operation"""

    def test_run_full_cleanup_dry_run(self, db_connection, clean_test_data):
        """Test full cleanup in dry-run mode"""
        cursor = db_connection.cursor()

        # Create old data
        old_date = datetime.utcnow() - timedelta(days=1100)

        cursor.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, start_time, end_time, message_count, created_at)
            VALUES ('test_full_old', 'test_user', %s, %s, 1, %s)
        """, (old_date, old_date, old_date))

        cursor.execute("""
            INSERT INTO conversation_messages
            (session_id, role, content, timestamp, created_at)
            VALUES ('test_full_old', 'user', 'Test', %s, %s)
        """, (old_date, old_date))

        cursor.execute("""
            INSERT INTO user_interaction_summaries
            (user_id, total_conversations, total_messages, preferred_language,
             last_interaction, created_at)
            VALUES ('test_full_user', 5, 20, 'en', %s, %s)
        """, (old_date, old_date))

        db_connection.commit()

        # Run full cleanup
        results = run_full_cleanup(
            db_connection,
            conversation_retention_days=90,
            summary_retention_days=730,
            dry_run=True
        )

        # Verify both operations ran
        assert 'conversations' in results
        assert 'summaries' in results

        assert results['conversations'].conversations_deleted >= 1
        assert results['summaries'].summaries_anonymized >= 1

        # Verify nothing deleted (dry run)
        cursor.execute("SELECT COUNT(*) FROM conversation_sessions WHERE session_id = 'test_full_old'")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT COUNT(*) FROM user_interaction_summaries WHERE user_id = 'test_full_user'")
        assert cursor.fetchone()[0] == 1


class TestAuditLogging:
    """Test audit trail logging"""

    def test_cleanup_creates_audit_log(self, db_connection, clean_test_data):
        """Test that cleanup operations are logged"""
        cursor = db_connection.cursor()

        # Ensure audit log table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_retention_audit_log (
                id SERIAL PRIMARY KEY,
                action VARCHAR(100) NOT NULL,
                details JSONB NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_connection.commit()

        # Run cleanup
        cleanup_old_conversations(db_connection, retention_days=90, dry_run=False)

        # Verify audit log entry
        cursor.execute("""
            SELECT COUNT(*) FROM data_retention_audit_log
            WHERE action = 'cleanup_old_conversations'
        """)

        count = cursor.fetchone()[0]
        assert count >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
