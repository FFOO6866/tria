#!/usr/bin/env python3
"""Check embedding generation progress"""
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

database_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(database_url)
cur = conn.cursor()

# Count total products
cur.execute("SELECT COUNT(*) FROM products WHERE is_active = TRUE")
total = cur.fetchone()[0]

# Count products with embeddings
cur.execute("SELECT COUNT(*) FROM products WHERE is_active = TRUE AND embedding IS NOT NULL AND embedding != ''")
with_embeddings = cur.fetchone()[0]

# Calculate progress
percentage = (with_embeddings / total * 100) if total > 0 else 0

print("=" * 70)
print("EMBEDDING GENERATION PROGRESS")
print("=" * 70)
print(f"\nTotal active products: {total:,}")
print(f"Products with embeddings: {with_embeddings:,}")
print(f"Remaining: {total - with_embeddings:,}")
print(f"Progress: {percentage:.2f}%")
print("\n" + "=" * 70)

conn.close()
