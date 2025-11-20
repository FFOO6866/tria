#!/usr/bin/env python3
"""Simple cache test - no Unicode emojis"""
import requests
import time
import uuid
import json

base_url = "http://localhost:8003"
query = "What is your refund policy?"
session_id = f"cache_test_{uuid.uuid4().hex[:8]}"

print("\n" + "="*60)
print("CACHE INTEGRATION TEST")
print("="*60)
print()

# Request 1
print("Request 1: Sending query (expecting cache MISS)...")
start1 = time.time()
response1 = requests.post(
    f"{base_url}/api/chatbot",
    json={"message": query, "session_id": session_id},
    headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
    timeout=60
)
latency1 = (time.time() - start1) * 1000

if response1.status_code == 200:
    data1 = response1.json()
    from_cache1 = data1.get("metadata", {}).get("from_cache", False)
    print(f"SUCCESS - Latency: {latency1:.0f}ms, From cache: {from_cache1}")
else:
    print(f"FAILED - HTTP {response1.status_code}")
    exit(1)

print()

# Wait for cache write
time.sleep(2)

# Request 2 - identical query
print("Request 2: Sending identical query (expecting cache HIT)...")
start2 = time.time()
response2 = requests.post(
    f"{base_url}/api/chatbot",
    json={"message": query, "session_id": session_id},
    headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
    timeout=60
)
latency2 = (time.time() - start2) * 1000

if response2.status_code == 200:
    data2 = response2.json()
    from_cache2 = data2.get("metadata", {}).get("from_cache", False)
    print(f"SUCCESS - Latency: {latency2:.0f}ms, From cache: {from_cache2}")
else:
    print(f"FAILED - HTTP {response2.status_code}")
    exit(1)

print()
print("="*60)
print("RESULTS:")
print(f"  Request 1: {latency1:.0f}ms (from_cache={from_cache1})")
print(f"  Request 2: {latency2:.0f}ms (from_cache={from_cache2})")
print(f"  Speedup: {latency1/latency2:.1f}x")
print()

if from_cache2:
    print("SUCCESS: Cache is working!")
    print(f"  Performance improvement: {latency1/latency2:.1f}x faster")
else:
    print("FAILED: Cache not working")
    print(f"  Second request should have been from cache")
    print()
    print("Debug:")
    print(f"  Response 1 metadata: {json.dumps(data1.get('metadata', {}), indent=2)}")
    print(f"  Response 2 metadata: {json.dumps(data2.get('metadata', {}), indent=2)}")
    exit(1)
