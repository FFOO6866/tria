#!/usr/bin/env python3
"""
Quick Smoke Test After Deployment
=================================

Runs basic sanity checks to verify the system is operational.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --host localhost --port 8000
"""

import sys
import argparse
import time
import json
import requests
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_ok(msg):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def test_health(base_url: str):
    """Test health check endpoint"""
    print("\n1. Testing Health Check...")
    print("-" * 50)

    try:
        start = time.time()
        r = requests.get(f"{base_url}/health", timeout=10)
        duration = (time.time() - start) * 1000

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        data = r.json()
        assert "status" in data, "Missing 'status' in response"

        print_ok(f"Health check passed ({duration:.0f}ms)")
        print(f"     Status: {data.get('status', 'unknown')}")

        if "components" in data:
            print("     Components:")
            for comp, status in data["components"].items():
                print(f"       - {comp}: {status}")

        return True

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server")
        print("     Is the server running?")
        print(f"     Try: uvicorn src.enhanced_api:app --host 0.0.0.0 --port {base_url.split(':')[-1]}")
        return False

    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_chat(base_url: str):
    """Test chat endpoint"""
    print("\n2. Testing Chat Endpoint...")
    print("-" * 50)

    try:
        test_message = "What is your return policy?"
        print_info(f"Sending message: '{test_message}'")

        start = time.time()
        r = requests.post(
            f"{base_url}/api/v1/chat",
            json={"message": test_message},
            timeout=30
        )
        duration = (time.time() - start) * 1000

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        data = r.json()
        assert "response" in data, "Missing 'response' in data"

        response_text = data.get("response", "")
        assert len(response_text) > 0, "Empty response"

        print_ok(f"Chat endpoint working ({duration:.0f}ms)")
        print(f"     Response length: {len(response_text)} chars")
        print(f"     Preview: {response_text[:100]}...")

        # Check for metadata
        if "metadata" in data:
            meta = data["metadata"]
            print(f"     Intent: {meta.get('intent', 'unknown')}")
            print(f"     Confidence: {meta.get('confidence', 0):.2f}")

        return True

    except requests.exceptions.Timeout:
        print_error("Request timeout (>30s)")
        return False

    except Exception as e:
        print_error(f"Chat test failed: {e}")
        return False


def test_streaming(base_url: str):
    """Test streaming endpoint"""
    print("\n3. Testing Streaming Endpoint...")
    print("-" * 50)

    try:
        test_message = "I need to place an order for office supplies"
        print_info(f"Sending message: '{test_message}'")

        start = time.time()
        first_chunk_time = None
        chunk_count = 0
        total_content = ""

        r = requests.post(
            f"{base_url}/api/v1/chat/stream",
            json={"message": test_message},
            stream=True,
            timeout=60
        )

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        for line in r.iter_lines():
            if not line:
                continue

            # Decode line
            line_str = line.decode('utf-8')

            # Skip comments
            if line_str.startswith(':'):
                continue

            # Parse SSE data
            if line_str.startswith('data: '):
                if first_chunk_time is None:
                    first_chunk_time = (time.time() - start) * 1000

                chunk_count += 1
                data_str = line_str[6:]  # Remove 'data: ' prefix

                try:
                    chunk_data = json.loads(data_str)

                    # Extract content
                    if "chunk" in chunk_data:
                        total_content += chunk_data["chunk"]
                    elif "status" in chunk_data:
                        status = chunk_data["status"]
                        if status in ["thinking", "classifying", "generating"]:
                            print_info(f"Status: {status}")

                except json.JSONDecodeError:
                    # Raw text chunk
                    total_content += data_str

        total_time = (time.time() - start) * 1000

        print_ok(f"Streaming endpoint working")
        print(f"     First chunk: {first_chunk_time:.0f}ms")
        print(f"     Total time: {total_time:.0f}ms")
        print(f"     Chunks: {chunk_count}")
        print(f"     Content length: {len(total_content)} chars")

        if first_chunk_time and first_chunk_time > 2000:
            print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} First chunk took >{first_chunk_time:.0f}ms (target: <1s)")

        return True

    except requests.exceptions.Timeout:
        print_error("Stream timeout (>60s)")
        return False

    except Exception as e:
        print_error(f"Streaming test failed: {e}")
        return False


def test_cache_stats(base_url: str):
    """Test cache stats endpoint"""
    print("\n4. Testing Cache Stats...")
    print("-" * 50)

    try:
        start = time.time()
        r = requests.get(f"{base_url}/api/v1/cache/stats", timeout=10)
        duration = (time.time() - start) * 1000

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        stats = r.json()

        print_ok(f"Cache stats available ({duration:.0f}ms)")

        # Display stats
        if "l1_hits" in stats:
            total_hits = stats.get("l1_hits", 0) + stats.get("l2_hits", 0) + stats.get("l3_hits", 0) + stats.get("l4_hits", 0)
            misses = stats.get("misses", 0)
            total = total_hits + misses

            if total > 0:
                hit_rate = (total_hits / total) * 100
                print(f"     Hit rate: {hit_rate:.1f}%")
                print(f"     L1 hits: {stats.get('l1_hits', 0)}")
                print(f"     L2 hits: {stats.get('l2_hits', 0)}")
                print(f"     L3 hits: {stats.get('l3_hits', 0)}")
                print(f"     L4 hits: {stats.get('l4_hits', 0)}")
                print(f"     Misses: {misses}")
            else:
                print("     No cache data yet (empty cache)")

        return True

    except Exception as e:
        print_error(f"Cache stats test failed: {e}")
        return False


def test_metrics(base_url: str):
    """Test metrics endpoint"""
    print("\n5. Testing Metrics Endpoint...")
    print("-" * 50)

    try:
        start = time.time()
        r = requests.get(f"{base_url}/api/v1/metrics", timeout=10)
        duration = (time.time() - start) * 1000

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

        metrics = r.json()

        print_ok(f"Metrics available ({duration:.0f}ms)")

        # Display key metrics
        if "performance" in metrics:
            perf = metrics["performance"]
            print(f"     Mean latency: {perf.get('mean_latency_ms', 0):.0f}ms")
            print(f"     P95 latency: {perf.get('p95_latency_ms', 0):.0f}ms")

        if "requests" in metrics:
            req = metrics["requests"]
            total = req.get("total", 0)
            successful = req.get("successful", 0)
            if total > 0:
                success_rate = (successful / total) * 100
                print(f"     Success rate: {success_rate:.1f}%")
                print(f"     Total requests: {total}")

        if "costs" in metrics:
            costs = metrics["costs"]
            print(f"     OpenAI calls: {costs.get('openai_calls', 0)}")
            print(f"     Total cost: ${costs.get('total_cost_usd', 0):.4f}")

        return True

    except Exception as e:
        print_error(f"Metrics test failed: {e}")
        return False


def main():
    """Run all smoke tests"""
    parser = argparse.ArgumentParser(description="Run smoke tests on deployed API")
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="API port (default: 8000)")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print("=" * 70)
    print("Smoke Test Suite")
    print("=" * 70)
    print(f"Target: {base_url}")
    print()

    tests = [
        ("Health Check", test_health),
        ("Chat Endpoint", test_chat),
        ("Streaming Endpoint", test_streaming),
        ("Cache Stats", test_cache_stats),
        ("Metrics", test_metrics),
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func(base_url)
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results[name] = False

        # Small delay between tests
        time.sleep(0.5)

    # Summary
    print("\n" + "=" * 70)
    print("SMOKE TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for name, result in results.items():
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if result else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"{status} {name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if all(results.values()):
        print(f"\n{Colors.GREEN}SMOKE TESTS: ALL PASSED{Colors.RESET}")
        print("\nSystem is operational and ready for further testing.")
        return 0
    else:
        print(f"\n{Colors.RED}SMOKE TESTS: FAILURES DETECTED{Colors.RESET}")
        print("\nPlease check the errors above and fix before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
