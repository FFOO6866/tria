#!/usr/bin/env python3
"""Verify database connection and products table"""
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

database_url = os.getenv('DATABASE_URL')
print(f"Connecting to: {database_url.replace('dev-password-123', '***')}")

conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Check if products table exists
cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'products'")
exists = cur.fetchone()[0] > 0
print(f"\nProducts table exists: {exists}")

if exists:
    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]
    print(f"Current products count: {count}")

    # Check if embeddings exist
    cur.execute("SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL AND embedding != ''")
    embeddings_count = cur.fetchone()[0]
    print(f"Products with embeddings: {embeddings_count}")
else:
    print("\n⚠️  Products table does not exist - need to create schema first")

conn.close()
