"""
Test ChromaDB Concurrent Access
================================

Tests thread-safe ChromaDB client under concurrent load.
"""

import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.chroma_client import get_chroma_client


def test_concurrent_access(thread_id: int) -> dict:
    """Test ChromaDB access from a single thread"""
    try:
        start_time = time.time()

        # Get client (should reuse singleton)
        client = get_chroma_client()

        # Try to list collections
        collections = client.list_collections()

        duration_ms = (time.time() - start_time) * 1000

        return {
            "thread_id": thread_id,
            "success": True,
            "duration_ms": duration_ms,
            "collections_count": len(collections),
            "error": None
        }

    except Exception as e:
        return {
            "thread_id": thread_id,
            "success": False,
            "duration_ms": 0,
            "collections_count": 0,
            "error": str(e)
        }


def main():
    """Run concurrent access test"""
    print("=" * 80)
    print("ChromaDB Concurrent Access Test")
    print("=" * 80)
    print()

    num_threads = 50
    print(f"Testing with {num_threads} concurrent threads...")
    print()

    start_time = time.time()

    # Run concurrent requests
    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(test_concurrent_access, i) for i in range(num_threads)]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            # Print progress
            if len(results) % 10 == 0:
                success_count = sum(1 for r in results if r["success"])
                print(f"  Progress: {len(results)}/{num_threads} - {success_count} successful")

    duration = time.time() - start_time

    # Analyze results
    print()
    print("=" * 80)
    print("Results")
    print("=" * 80)
    print()

    success_count = sum(1 for r in results if r["success"])
    failed_count = sum(1 for r in results if not r["success"])

    print(f"Total Threads:    {num_threads}")
    print(f"Successful:       {success_count} ({success_count/num_threads*100:.1f}%)")
    print(f"Failed:           {failed_count} ({failed_count/num_threads*100:.1f}%)")
    print(f"Total Duration:   {duration:.2f}s")
    print()

    if success_count > 0:
        successful_results = [r for r in results if r["success"]]
        durations = [r["duration_ms"] for r in successful_results]

        print("Performance:")
        print(f"  Mean:   {sum(durations)/len(durations):.2f}ms")
        print(f"  Min:    {min(durations):.2f}ms")
        print(f"  Max:    {max(durations):.2f}ms")
        print()

    if failed_count > 0:
        print("Errors:")
        failed_results = [r for r in results if not r["success"]]
        for result in failed_results[:5]:  # Show first 5 errors
            print(f"  Thread {result['thread_id']}: {result['error']}")
        if failed_count > 5:
            print(f"  ... and {failed_count - 5} more errors")
        print()

    # Final verdict
    if success_count == num_threads:
        print("[OK] All threads succeeded - ChromaDB is thread-safe!")
    elif success_count > num_threads * 0.9:
        print("[WARNING] Most threads succeeded, but some failures occurred")
    else:
        print("[ERROR] Many failures - ChromaDB concurrent access has issues")

    print()
    print("=" * 80)

    return 0 if success_count == num_threads else 1


if __name__ == "__main__":
    exit(main())
