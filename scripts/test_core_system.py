"""
Test Core System Without Xero
Verifies database, RAG, and chat functionality
"""
import sys
sys.path.insert(0, 'src')

from database import get_db_engine
from sqlalchemy import text
from rag.retrieval import search_policies, search_faqs

print("=" * 70)
print("CORE SYSTEM TEST (WITHOUT XERO)")
print("=" * 70)

# Test 1: Database Connection
print("\n[1/4] Testing Database Connection...")
try:
    engine = get_db_engine()
    with engine.connect() as conn:
        # Check tables exist
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [row[0] for row in result]
        print(f"  [OK] Database connected")
        print(f"  [OK] Found {len(tables)} tables: {', '.join(tables)}")

        # Count data
        outlets = conn.execute(text('SELECT COUNT(*) FROM outlets')).scalar()
        products = conn.execute(text('SELECT COUNT(*) FROM products WHERE is_active=true')).scalar()
        orders = conn.execute(text('SELECT COUNT(*) FROM orders')).scalar()

        print(f"  [OK] Data counts:")
        print(f"      - Outlets: {outlets}")
        print(f"      - Products (active): {products}")
        print(f"      - Orders: {orders}")

        db_ok = True
except Exception as e:
    print(f"  [FAIL] Database error: {e}")
    db_ok = False

# Test 2: RAG - Policies
print("\n[2/4] Testing RAG - Policy Retrieval...")
try:
    import os
    api_key = os.getenv('OPENAI_API_KEY')
    results = search_policies(query="What is your refund policy?", api_key=api_key, top_n=2)
    print(f"  [OK] Retrieved {len(results)} policy documents")
    if results:
        print(f"  [OK] Sample: {results[0].get('text', '')[:100]}...")
    rag_policies_ok = True
except Exception as e:
    print(f"  [FAIL] RAG policies error: {e}")
    rag_policies_ok = False

# Test 3: RAG - FAQs
print("\n[3/4] Testing RAG - FAQ Retrieval...")
try:
    results = search_faqs(query="Do you deliver on weekends?", api_key=api_key, top_n=2)
    print(f"  [OK] Retrieved {len(results)} FAQ documents")
    if results:
        print(f"  [OK] Sample: {results[0].get('text', '')[:100]}...")
    rag_faqs_ok = True
except Exception as e:
    print(f"  [FAIL] RAG FAQs error: {e}")
    rag_faqs_ok = False

# Test 4: OpenAI Connection
print("\n[4/4] Testing OpenAI API Connection...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[{"role": "user", "content": "Say 'API test successful' in exactly 3 words"}],
        max_tokens=10
    )
    result = response.choices[0].message.content
    print(f"  [OK] OpenAI API connected")
    print(f"  [OK] Response: {result}")
    openai_ok = True
except Exception as e:
    print(f"  [FAIL] OpenAI error: {e}")
    openai_ok = False

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
checks = [
    ("Database", db_ok),
    ("RAG - Policies", rag_policies_ok),
    ("RAG - FAQs", rag_faqs_ok),
    ("OpenAI API", openai_ok)
]

passed = sum(1 for _, ok in checks if ok)
total = len(checks)

for name, ok in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}")

print(f"\nCore System Score: {passed}/{total} ({int(passed/total*100)}%)")

if passed == total:
    print("\n[SUCCESS] All core components working!")
    print("System can run WITHOUT Xero integration.")
else:
    print(f"\n[WARNING] {total-passed} component(s) failing")

print("\n" + "=" * 70)
