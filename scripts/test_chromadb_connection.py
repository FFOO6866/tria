"""
Test ChromaDB Connection
========================

Simple script to test if ChromaDB is working and identify issues.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.config import Settings

def test_chromadb():
    """Test ChromaDB connection"""
    print("=" * 80)
    print("ChromaDB Connection Test")
    print("=" * 80)
    print()

    # Check version
    print(f"ChromaDB version: {chromadb.__version__}")
    print()

    # Test 1: Try basic persistent client
    print("Test 1: Basic PersistentClient...")
    try:
        persist_dir = Path(__file__).parent.parent / "data" / "chromadb"
        persist_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Persist directory: {persist_dir}")
        print(f"  Directory exists: {persist_dir.exists()}")

        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )

        print("  [OK] Client created successfully!")

        # Try to list collections
        collections = client.list_collections()
        print(f"  Collections: {[c.name for c in collections]}")
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print()

    # Test 2: Try EphemeralClient (in-memory)
    print("Test 2: EphemeralClient (in-memory)...")
    try:
        client = chromadb.EphemeralClient()
        print("  [OK] Ephemeral client created successfully!")

        # Try to create a collection
        collection = client.create_collection("test_collection")
        print(f"  [OK] Collection created: {collection.name}")
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        print(f"  Error type: {type(e).__name__}")
        print()

    # Test 3: Check SQLite database
    print("Test 3: Check SQLite database...")
    try:
        sqlite_path = Path(__file__).parent.parent / "data" / "chromadb" / "chroma.sqlite3"
        if sqlite_path.exists():
            print(f"  [OK] SQLite database exists: {sqlite_path}")
            print(f"  Size: {sqlite_path.stat().st_size / 1024:.2f} KB")
        else:
            print(f"  [ERROR] SQLite database not found: {sqlite_path}")
        print()

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        print()

    # Test 4: Try using HttpClient (if server is running)
    print("Test 4: HttpClient (requires ChromaDB server)...")
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        print("  [OK] HTTP client created!")
        collections = client.list_collections()
        print(f"  Collections: {[c.name for c in collections]}")
        print()

    except Exception as e:
        print(f"  [INFO] Server not running (expected): {str(e)}")
        print()

    print("=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_chromadb()
