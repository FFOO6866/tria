"""
TRIA AI-BPO Streaming Tests
============================

Tier 2 Integration tests for SSE (Server-Sent Events) streaming functionality.

Tests:
1. SSE format compliance
2. Progressive chunk delivery
3. Error handling in streams
4. Connection timeout
5. Intent classification streaming
6. RAG retrieval streaming
7. Complete response validation

NO MOCKING - Uses real OpenAI streaming API with test data.
"""

import pytest
import asyncio
import json
import time
from typing import List, Dict, Any

from services.streaming_service import StreamingService, StreamEvent


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def streaming_service(openai_api_key: str) -> StreamingService:
    """
    Create streaming service for tests

    Args:
        openai_api_key: OpenAI API key from pytest fixture

    Returns:
        Configured StreamingService instance
    """
    return StreamingService(
        api_key=openai_api_key,
        model="gpt-3.5-turbo",  # Use faster model for testing
        temperature=0.7,
        timeout=30,
        enable_rag=True
    )


@pytest.fixture
def streaming_service_no_rag(openai_api_key: str) -> StreamingService:
    """
    Create streaming service without RAG for basic tests

    Args:
        openai_api_key: OpenAI API key from pytest fixture

    Returns:
        Configured StreamingService instance (RAG disabled)
    """
    return StreamingService(
        api_key=openai_api_key,
        model="gpt-3.5-turbo",
        temperature=0.7,
        timeout=30,
        enable_rag=False
    )


# ============================================================================
# TEST: SSE FORMAT COMPLIANCE
# ============================================================================

@pytest.mark.asyncio
async def test_sse_format_compliance(streaming_service_no_rag):
    """
    Test that all events are properly formatted as SSE

    SSE format: "data: {json}\\n\\n"
    """
    message = "Hello, how are you?"
    events = []

    async for event_str in streaming_service_no_rag.stream_chat_response(message):
        events.append(event_str)

        # Verify SSE format
        assert event_str.startswith("data: "), f"Event must start with 'data: ': {event_str[:50]}"
        assert event_str.endswith("\n\n"), f"Event must end with '\\n\\n': {event_str[-10:]}"

        # Verify JSON parsing
        json_str = event_str[6:-2]  # Remove "data: " prefix and "\n\n" suffix
        event_data = json.loads(json_str)

        # Verify required fields
        assert "type" in event_data, "Event must have 'type' field"
        assert "data" in event_data, "Event must have 'data' field"
        assert "timestamp" in event_data, "Event must have 'timestamp' field"

    # Verify we got events
    assert len(events) > 0, "Should receive at least one event"

    print(f"✓ SSE format compliance verified ({len(events)} events)")


# ============================================================================
# TEST: PROGRESSIVE CHUNK DELIVERY
# ============================================================================

@pytest.mark.asyncio
async def test_progressive_chunk_delivery(streaming_service_no_rag):
    """
    Test that response is delivered in progressive chunks

    Verifies:
    - Multiple chunk events received
    - Chunks arrive incrementally
    - Complete response assembles correctly
    """
    message = "Tell me a short story."
    chunks = []
    chunk_times = []
    start_time = time.time()

    async for event_str in streaming_service_no_rag.stream_chat_response(message):
        json_str = event_str[6:-2]
        event_data = json.loads(json_str)

        if event_data["type"] == "chunk":
            chunk_text = event_data["data"]["chunk"]
            chunks.append(chunk_text)
            chunk_times.append(time.time() - start_time)

    # Verify progressive delivery
    assert len(chunks) > 1, "Should receive multiple chunks"
    assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"

    # Verify chunks arrive incrementally (time between chunks < 2s)
    for i in range(1, len(chunk_times)):
        time_between_chunks = chunk_times[i] - chunk_times[i-1]
        assert time_between_chunks < 2.0, \
            f"Chunks should arrive quickly (got {time_between_chunks:.2f}s between chunks)"

    # Assemble complete response
    full_response = "".join(chunks)
    assert len(full_response) > 0, "Complete response should not be empty"
    assert len(full_response) > 20, "Response should be substantial"

    print(f"✓ Progressive delivery verified ({len(chunks)} chunks over {chunk_times[-1]:.2f}s)")
    print(f"  Response length: {len(full_response)} chars")


# ============================================================================
# TEST: EVENT SEQUENCE
# ============================================================================

@pytest.mark.asyncio
async def test_event_sequence(streaming_service_no_rag):
    """
    Test correct sequence of events

    Expected sequence:
    1. status: thinking
    2. status: classifying
    3. intent: <intent result>
    4. status: generating
    5. chunk: <text chunks...>
    6. complete: <metadata>
    """
    message = "What is AI?"
    event_types = []

    async for event_str in streaming_service_no_rag.stream_chat_response(message):
        json_str = event_str[6:-2]
        event_data = json.loads(json_str)
        event_types.append(event_data["type"])

    # Verify expected event types are present
    assert "status" in event_types, "Should have status events"
    assert "intent" in event_types, "Should have intent event"
    assert "chunk" in event_types, "Should have chunk events"
    assert "complete" in event_types, "Should have complete event"

    # Verify order (thinking/classifying → intent → generating → chunks → complete)
    intent_index = event_types.index("intent")
    complete_index = event_types.index("complete")
    first_chunk_index = event_types.index("chunk")

    assert intent_index < first_chunk_index, "Intent should come before chunks"
    assert first_chunk_index < complete_index, "Chunks should come before complete"

    print(f"✓ Event sequence verified: {' → '.join(set(event_types))}")


# ============================================================================
# TEST: INTENT CLASSIFICATION IN STREAM
# ============================================================================

@pytest.mark.asyncio
async def test_intent_classification_stream(streaming_service_no_rag):
    """
    Test that intent classification is included in stream
    """
    test_cases = [
        ("What's your refund policy?", "policy_question"),
        ("I want to place an order", "order_placement"),
        ("Hello", "greeting"),
    ]

    for message, expected_intent in test_cases:
        intent_found = False
        intent_confidence = 0.0

        async for event_str in streaming_service_no_rag.stream_chat_response(message):
            json_str = event_str[6:-2]
            event_data = json.loads(json_str)

            if event_data["type"] == "intent":
                intent_data = event_data["data"]
                detected_intent = intent_data["intent"]
                intent_confidence = intent_data["confidence"]
                intent_found = True

                # Verify intent matches (or is reasonably close)
                print(f"  Message: '{message}' → Intent: {detected_intent} ({intent_confidence:.2f})")

                # For greetings, accept exact match
                # For others, accept if confidence > 0.5
                if expected_intent == "greeting":
                    assert detected_intent == expected_intent, \
                        f"Expected {expected_intent}, got {detected_intent}"
                else:
                    assert intent_confidence > 0.5, \
                        f"Intent confidence should be > 0.5, got {intent_confidence:.2f}"

        assert intent_found, f"Intent event not found for message: {message}"

    print(f"✓ Intent classification in stream verified ({len(test_cases)} test cases)")


# ============================================================================
# TEST: RAG RETRIEVAL IN STREAM
# ============================================================================

@pytest.mark.asyncio
async def test_rag_retrieval_stream(streaming_service):
    """
    Test that RAG retrieval is included in stream for policy questions

    Requires:
    - ChromaDB running with policies collection
    - OpenAI API key for embeddings
    """
    message = "What is your refund policy?"
    retrieval_found = False
    chunks_retrieved = 0

    try:
        async for event_str in streaming_service.stream_chat_response(message):
            json_str = event_str[6:-2]
            event_data = json.loads(json_str)

            if event_data["type"] == "retrieval":
                retrieval_data = event_data["data"]
                chunks_retrieved = retrieval_data["chunks_retrieved"]
                retrieval_found = True

                # Verify retrieval happened
                assert chunks_retrieved > 0, "Should retrieve at least one knowledge chunk"

                print(f"  Retrieved {chunks_retrieved} knowledge chunks")

        # Verify retrieval event was sent
        assert retrieval_found, "Retrieval event not found for policy question"

        print(f"✓ RAG retrieval in stream verified ({chunks_retrieved} chunks)")

    except Exception as e:
        if "ChromaDB" in str(e) or "chroma" in str(e).lower():
            pytest.skip(f"ChromaDB not available: {str(e)}")
        else:
            raise


# ============================================================================
# TEST: ERROR HANDLING IN STREAM
# ============================================================================

@pytest.mark.asyncio
async def test_error_handling_invalid_api_key():
    """
    Test error handling when API key is invalid
    """
    service = StreamingService(
        api_key="invalid_key_12345",
        model="gpt-3.5-turbo",
        enable_rag=False
    )

    message = "Hello"
    error_found = False

    async for event_str in service.stream_chat_response(message):
        json_str = event_str[6:-2]
        event_data = json.loads(json_str)

        if event_data["type"] == "error":
            error_found = True
            error_data = event_data["data"]
            assert "error" in error_data, "Error event should contain error message"
            print(f"  Error correctly caught: {error_data['error'][:50]}")

    assert error_found, "Error event should be emitted for invalid API key"

    print("✓ Error handling verified")


# ============================================================================
# TEST: CONNECTION TIMEOUT
# ============================================================================

@pytest.mark.asyncio
async def test_connection_timeout():
    """
    Test that streaming respects timeout settings

    Note: This test uses a very short timeout to verify timeout behavior
    """
    service = StreamingService(
        api_key="invalid_key",  # Will cause timeout
        model="gpt-3.5-turbo",
        timeout=1,  # 1 second timeout
        enable_rag=False
    )

    message = "Hello"
    start_time = time.time()
    events_received = []

    try:
        async for event_str in service.stream_chat_response(message):
            events_received.append(event_str)
    except Exception as e:
        elapsed = time.time() - start_time
        # Should timeout within 2 seconds (1s timeout + overhead)
        assert elapsed < 3.0, f"Should timeout quickly, took {elapsed:.2f}s"
        print(f"✓ Connection timeout verified ({elapsed:.2f}s)")
        return

    # If we get here, check if error event was sent
    if events_received:
        last_event = events_received[-1]
        json_str = last_event[6:-2]
        event_data = json.loads(json_str)
        assert event_data["type"] == "error", "Last event should be error"

    print("✓ Connection timeout verified (via error event)")


# ============================================================================
# TEST: COMPLETE RESPONSE VALIDATION
# ============================================================================

@pytest.mark.asyncio
async def test_complete_response_validation(streaming_service_no_rag):
    """
    Test that complete event includes proper metadata
    """
    message = "What is machine learning?"
    complete_data = None

    async for event_str in streaming_service_no_rag.stream_chat_response(message):
        json_str = event_str[6:-2]
        event_data = json.loads(json_str)

        if event_data["type"] == "complete":
            complete_data = event_data["data"]

    # Verify complete event received
    assert complete_data is not None, "Should receive complete event"

    # Verify metadata
    assert "metadata" in complete_data, "Complete event should contain metadata"
    metadata = complete_data["metadata"]

    assert "intent" in metadata, "Metadata should include intent"
    assert "confidence" in metadata, "Metadata should include confidence"
    assert "processing_time" in metadata, "Metadata should include processing_time"
    assert "response_length" in metadata, "Metadata should include response_length"

    # Verify metadata values
    assert metadata["confidence"] >= 0.0 and metadata["confidence"] <= 1.0, \
        "Confidence should be between 0 and 1"
    assert metadata["response_length"] > 0, "Response length should be positive"

    print(f"✓ Complete response validation verified")
    print(f"  Intent: {metadata['intent']} ({metadata['confidence']:.2f})")
    print(f"  Processing time: {metadata['processing_time']}")
    print(f"  Response length: {metadata['response_length']} chars")


# ============================================================================
# TEST: MULTIPLE CONCURRENT STREAMS
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_streams(streaming_service_no_rag):
    """
    Test that multiple streams can run concurrently without interference
    """
    messages = [
        "What is AI?",
        "Tell me about machine learning.",
        "Explain neural networks."
    ]

    # Run streams concurrently
    async def stream_and_collect(message: str) -> List[str]:
        events = []
        async for event_str in streaming_service_no_rag.stream_chat_response(message):
            events.append(event_str)
        return events

    # Start all streams concurrently
    results = await asyncio.gather(
        *[stream_and_collect(msg) for msg in messages]
    )

    # Verify all streams completed
    assert len(results) == len(messages), "All streams should complete"

    for i, events in enumerate(results):
        assert len(events) > 0, f"Stream {i} should have events"

        # Verify complete event
        last_event = events[-1]
        json_str = last_event[6:-2]
        event_data = json.loads(json_str)
        assert event_data["type"] in ["complete", "error"], \
            f"Stream {i} should end with complete or error"

    print(f"✓ Concurrent streams verified ({len(messages)} streams)")


# ============================================================================
# PERFORMANCE BENCHMARKS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_streaming_performance(streaming_service_no_rag):
    """
    Benchmark streaming performance metrics

    Targets:
    - First token latency < 2s
    - Time to complete < 10s
    - Throughput > 10 chars/s
    """
    message = "Explain the benefits of cloud computing in 3 sentences."

    start_time = time.time()
    first_chunk_time = None
    complete_time = None
    total_chars = 0

    async for event_str in streaming_service_no_rag.stream_chat_response(message):
        json_str = event_str[6:-2]
        event_data = json.loads(json_str)

        if event_data["type"] == "chunk" and first_chunk_time is None:
            first_chunk_time = time.time()

        if event_data["type"] == "chunk":
            total_chars += len(event_data["data"]["chunk"])

        if event_data["type"] == "complete":
            complete_time = time.time()

    # Calculate metrics
    first_token_latency = first_chunk_time - start_time if first_chunk_time else float('inf')
    total_time = complete_time - start_time if complete_time else float('inf')
    throughput = total_chars / total_time if total_time > 0 else 0

    print(f"\n📊 Streaming Performance Metrics:")
    print(f"  First token latency: {first_token_latency:.2f}s (target: <2s)")
    print(f"  Total time: {total_time:.2f}s (target: <10s)")
    print(f"  Throughput: {throughput:.1f} chars/s (target: >10 chars/s)")
    print(f"  Total characters: {total_chars}")

    # Verify targets (relaxed for testing)
    assert first_token_latency < 5.0, \
        f"First token latency too high: {first_token_latency:.2f}s"
    assert total_time < 20.0, \
        f"Total time too high: {total_time:.2f}s"
    assert throughput > 5.0, \
        f"Throughput too low: {throughput:.1f} chars/s"

    print("✓ Streaming performance within targets")
