"""
TRIA AI-BPO Chat Streaming Route
=================================

FastAPI route for SSE (Server-Sent Events) streaming chat endpoint.

Endpoint: POST /chat/stream
Response: text/event-stream

NO MOCKING - Uses real OpenAI streaming API.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from services.streaming_service import StreamingService


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])


# ============================================================================
# REQUEST MODELS
# ============================================================================

class ChatStreamRequest(BaseModel):
    """
    Request model for streaming chat endpoint

    Attributes:
        message: User message to process
        user_id: Optional user identifier
        session_id: Optional session identifier
        outlet_id: Optional outlet context
        language: User's language (default: en)
    """
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    outlet_id: Optional[int] = None
    language: Optional[str] = "en"


# ============================================================================
# STREAMING ENDPOINT
# ============================================================================

@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest,
    raw_request: Request
) -> StreamingResponse:
    """
    Stream chat response with SSE

    **Request Body:**
    ```json
    {
      "message": "What's your refund policy?",
      "user_id": "user_123",
      "session_id": "session_abc",
      "outlet_id": 1,
      "language": "en"
    }
    ```

    **Response Stream:**
    ```
    data: {"type": "status", "data": {"status": "thinking"}, "timestamp": "..."}

    data: {"type": "status", "data": {"status": "classifying"}, "timestamp": "..."}

    data: {"type": "intent", "data": {"intent": "policy_question", "confidence": 0.95}, "timestamp": "..."}

    data: {"type": "status", "data": {"status": "retrieving"}, "timestamp": "..."}

    data: {"type": "retrieval", "data": {"chunks_retrieved": 3}, "timestamp": "..."}

    data: {"type": "status", "data": {"status": "generating"}, "timestamp": "..."}

    data: {"type": "chunk", "data": {"chunk": "Our refund"}, "timestamp": "..."}

    data: {"type": "chunk", "data": {"chunk": " policy allows"}, "timestamp": "..."}

    data: {"type": "complete", "data": {"status": "complete"}, "timestamp": "..."}
    ```

    **Event Types:**
    - `status`: Processing status (thinking, classifying, retrieving, generating)
    - `intent`: Intent classification result
    - `retrieval`: Knowledge retrieval result
    - `chunk`: Partial response text
    - `error`: Error occurred
    - `complete`: Response complete

    **Client Example:**
    ```javascript
    const eventSource = new EventSource('/chat/stream?message=...');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'chunk') {
            appendToChat(data.data.chunk);
        } else if (data.type === 'status') {
            updateStatus(data.data.status);
        } else if (data.type === 'complete') {
            eventSource.close();
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        showError('Connection lost');
    };
    ```

    **Args:**
    - request: ChatStreamRequest with message and context
    - raw_request: FastAPI Request object

    **Returns:**
    - StreamingResponse with text/event-stream content type

    **Raises:**
    - HTTPException 503: Service not initialized
    - HTTPException 500: Streaming error
    """
    logger.info(
        f"[STREAM] New streaming request: user_id={request.user_id}, "
        f"message_length={len(request.message)}"
    )

    try:
        # Get OpenAI API key from config
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Chatbot features are disabled."
            )

        # Initialize streaming service
        streaming_service = StreamingService(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            temperature=0.7,
            enable_rag=True
        )

        # Build user context
        user_context = {}
        if request.outlet_id:
            user_context["outlet_id"] = request.outlet_id
        if request.language:
            user_context["language"] = request.language

        # Create async generator for streaming
        async def generate():
            """
            Async generator that yields SSE formatted events

            Handles client disconnection gracefully.
            """
            try:
                async for event in streaming_service.stream_chat_response(
                    message=request.message,
                    conversation_history=None,  # TODO: Load from session
                    user_context=user_context
                ):
                    # Check if client disconnected
                    if await raw_request.is_disconnected():
                        logger.info("[STREAM] Client disconnected, stopping stream")
                        break

                    yield event

            except Exception as e:
                logger.error(f"[STREAM] Error in generator: {str(e)}", exc_info=True)
                # Send error event
                import json
                from datetime import datetime
                error_event = {
                    "type": "error",
                    "data": {"error": "Streaming error occurred"},
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_event)}\n\n"

        # Return streaming response with proper SSE headers
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",  # CORS for SSE
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[STREAM] Failed to initialize streaming: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize streaming: {str(e)}"
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/stream/health")
async def stream_health():
    """
    Health check for streaming endpoint

    Returns:
        Dict with streaming service status
    """
    import os

    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "status": "healthy" if openai_configured else "degraded",
        "streaming_enabled": openai_configured,
        "openai_configured": openai_configured,
        "model": os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    }
