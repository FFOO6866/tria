#!/usr/bin/env python3
"""
Migrate Conversation Tables to SQLAlchemy Schema
=================================================

Adds missing columns from DataFlow schema to match SQLAlchemy ORM models.

Changes:
- Add embedding_id column to conversation_messages
- Add index for embedding_id
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from database import get_db_engine
from sqlalchemy import text

if __name__ == "__main__":
    print("=" * 70)
    print("MIGRATING CONVERSATION TABLES TO SQLALCHEMY SCHEMA")
    print("=" * 70)

    engine = get_db_engine()

    try:
        with engine.connect() as conn:
            # Add embedding_id column
            print("\n[1/2] Adding embedding_id column to conversation_messages...")
            try:
                conn.execute(text(
                    'ALTER TABLE conversation_messages ADD COLUMN embedding_id VARCHAR(100)'
                ))
                conn.commit()
                print("[OK] Column added")
            except Exception as e:
                if "already exists" in str(e):
                    print("[SKIP] Column already exists")
                else:
                    raise

            # Add index
            print("\n[2/2] Creating index on embedding_id...")
            try:
                conn.execute(text(
                    'CREATE INDEX IF NOT EXISTS idx_message_embedding ON conversation_messages(embedding_id)'
                ))
                conn.commit()
                print("[OK] Index created")
            except Exception as e:
                if "already exists" in str(e):
                    print("[SKIP] Index already exists")
                else:
                    raise

        print("\n" + "=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print("[OK] Conversation tables ready for SQLAlchemy ORM")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
