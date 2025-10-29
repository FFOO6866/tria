# TRIA AI Chatbot Frontend Components

## Overview

The frontend has been enhanced to support the new intelligent chatbot features with RAG-powered Q&A, multilingual support, and intent detection.

## Components

### 1. OrderInputPanel.tsx (Enhanced)

**Main WhatsApp-style chat interface with two modes:**

#### **Mode: 'chatbot'** (NEW - Intelligent Q&A)
- General Q&A support (policy questions, FAQs, etc.)
- Intent detection display (Order, Question, Status, Inquiry)
- Confidence scores for AI responses
- Language selector (EN/CN/MS)
- Session tracking with session ID display
- RAG citations for knowledge-based answers
- Typing indicators during API calls

#### **Mode: 'order'** (LEGACY - Order Processing)
- Original order processing functionality
- Backward compatible with existing DemoLayout
- Multi-agent order workflow

### 2. ConversationPanel.tsx (NEW)

**Dedicated conversation history viewer:**

- Full message history display
- Message metadata (timestamp, intent, confidence, language)
- RAG policy citations with relevance scores
- Different message types (text, order_confirmation, error, system)
- Export transcript functionality
- Mobile-responsive design

## Usage Examples

### Example 1: Chatbot Mode (Intelligent Q&A)

```typescript
import OrderInputPanel from '@/elements/OrderInputPanel';

function ChatbotDemo() {
  return (
    <OrderInputPanel
      mode="chatbot"  // Enable intelligent Q&A
    />
  );
}
```

**Features enabled in chatbot mode:**
- ✅ General Q&A (not just orders)
- ✅ Intent detection badges
- ✅ Confidence scores
- ✅ Language selector (EN/CN/MS)
- ✅ Session tracking
- ✅ RAG citations display
- ✅ Automatic chatbot API integration

### Example 2: Legacy Order Mode (Backward Compatible)

```typescript
import OrderInputPanel from '@/elements/OrderInputPanel';
import { processOrder } from '@/elements/api-client';

function OrderDemo() {
  const handleOrderSubmit = async (message: string, outlet: string) => {
    await processOrder({ whatsapp_message: message, outlet_name: outlet });
  };

  return (
    <OrderInputPanel
      mode="order"  // Original order processing
      onSubmit={handleOrderSubmit}
      isProcessing={false}
    />
  );
}
```

### Example 3: Using ConversationPanel

```typescript
import ConversationPanel from '@/elements/ConversationPanel';
import { ConversationalMessage } from '@/elements/types';

function ConversationHistory() {
  const [messages, setMessages] = useState<ConversationalMessage[]>([
    {
      id: 1,
      text: "What is your refund policy?",
      sender: "user",
      timestamp: "10:30 AM",
      type: "text"
    },
    {
      id: 2,
      text: "Our refund policy allows returns within 30 days...",
      sender: "bot",
      timestamp: "10:30 AM",
      intent: "ask_question",
      confidence: 0.95,
      language: "en",
      citations: [
        {
          policy_id: "refund_policy_v2",
          policy_name: "Refund and Returns Policy",
          section: "Section 3.1 - Return Window",
          relevance_score: 0.92
        }
      ],
      type: "text"
    }
  ]);

  const handleExport = async () => {
    await exportConversationTranscript(sessionId, 'txt');
  };

  return (
    <ConversationPanel
      messages={messages}
      sessionId="abc123def456"
      isTyping={false}
      onExportTranscript={handleExport}
    />
  );
}
```

## API Client Functions

### sendChatbotMessage()

```typescript
import { sendChatbotMessage, ChatbotRequest } from '@/elements/api-client';

// Send message to intelligent chatbot
const request: ChatbotRequest = {
  message: "What is your delivery policy?",
  session_id: "optional-session-id",  // Auto-generated if omitted
  outlet_name: "Pacific Pizza - Downtown",
  language: "en"  // or "zh", "ms"
};

const response = await sendChatbotMessage(request);

console.log(response.message);      // AI response text
console.log(response.intent);       // "ask_question"
console.log(response.confidence);   // 0.95
console.log(response.citations);    // RAG policy citations
console.log(response.session_id);   // Session ID for continuity
```

### getConversationHistory()

```typescript
import { getConversationHistory } from '@/elements/api-client';

// Get all conversations
const allConversations = await getConversationHistory();

// Get specific session
const session = await getConversationHistory("session-id-123");
```

### exportConversationTranscript()

```typescript
import { exportConversationTranscript } from '@/elements/api-client';

// Export as text file
await exportConversationTranscript("session-id-123", "txt");

// Export as JSON
await exportConversationTranscript("session-id-123", "json");
```

## TypeScript Types

### ConversationalMessage

```typescript
interface ConversationalMessage {
  id: number;
  session_id?: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
  intent?: MessageIntent;           // Detected intent
  confidence?: number;              // 0-1 confidence score
  language?: string;                // 'en', 'zh', 'ms'
  citations?: RAGCitation[];        // Knowledge base citations
  mode?: ChatMode;                  // 'order', 'query', 'status'
  type?: MessageType;               // 'text', 'order_confirmation', 'error', 'system'
  metadata?: Record<string, any>;
}
```

### RAGCitation

```typescript
interface RAGCitation {
  policy_id: string;                // Unique policy identifier
  policy_name: string;              // Human-readable policy name
  section: string;                  // Specific section reference
  relevance_score: number;          // 0-1 relevance score
  content?: string;                 // Optional content excerpt
}
```

### ChatbotRequest

```typescript
interface ChatbotRequest {
  message: string;                  // User message (required)
  session_id?: string;              // Session ID (auto-generated if omitted)
  outlet_name?: string;             // Outlet context
  mode?: ChatMode;                  // 'order', 'query', 'status'
  language?: string;                // 'en', 'zh', 'ms'
}
```

### ChatbotResponse

```typescript
interface ChatbotResponse {
  success: boolean;
  session_id: string;
  message: string;                  // AI response text
  intent: MessageIntent;            // Detected intent
  confidence: number;               // Intent confidence (0-1)
  language: string;                 // Response language
  citations?: RAGCitation[];        // Knowledge citations
  mode: ChatMode;
  context?: Record<string, any>;
  error?: string;
}
```

## UI Features

### Intent Badges

Messages automatically display intent badges based on detected intent:

- 📦 **Order** - `place_order` (green)
- ❓ **Question** - `ask_question` (blue)
- 📊 **Status** - `check_status` (purple)
- 💬 **Inquiry** - `general_inquiry` (gray)

### Language Support

Language selector in chatbot mode:
- 🇬🇧 English (`en`)
- 🇨🇳 中文 (`zh`)
- 🇲🇾 Bahasa Malaysia (`ms`)

### RAG Citations

When the chatbot answers using knowledge base policies, citations are displayed:

```
📚 Based on:
┌─────────────────────────────────────┐
│ Refund and Returns Policy           │
│ Section 3.1 - Return Window         │
│ 92% relevant                         │
└─────────────────────────────────────┘
```

### Session Tracking

Session ID is displayed in the header:
```
Session: abc123de...
```

Session ID persists across messages for conversation continuity.

### Typing Indicator

Animated typing dots display while waiting for chatbot response:
```
● ● ●
```

## Quick Reply Examples

### Chatbot Mode Quick Replies:
- ❓ Policy: "What is your return policy for damaged goods?"
- 📦 Order: "I need 600 x 10" and 200 x 12" pizza boxes..."
- 💰 Pricing: "What are your bulk pricing options?"
- 🚚 Delivery: "How long does delivery usually take?"

### Order Mode Quick Replies:
- 📦 Standard: "Need 600 x 10", 200 x 12" boxes..."
- ⚡ Urgent: "URGENT: Need 800 x 10" boxes ASAP!"
- 📊 Large: "Placing order for 1000 x 10" boxes..."

## Backend API Requirements

The frontend expects these backend endpoints:

### POST /api/chatbot
```json
Request:
{
  "message": "What is your refund policy?",
  "session_id": "abc123",
  "outlet_name": "Pacific Pizza - Downtown",
  "language": "en"
}

Response:
{
  "success": true,
  "session_id": "abc123",
  "message": "Our refund policy allows returns within 30 days...",
  "intent": "ask_question",
  "confidence": 0.95,
  "language": "en",
  "citations": [
    {
      "policy_id": "refund_policy_v2",
      "policy_name": "Refund and Returns Policy",
      "section": "Section 3.1",
      "relevance_score": 0.92
    }
  ],
  "mode": "query"
}
```

### GET /api/conversation/history?session_id={id}
```json
Response:
{
  "sessions": [...],
  "total_sessions": 5,
  "messages": [...]
}
```

### GET /api/conversation/export?session_id={id}&format={txt|json}
Returns downloadable file

### GET /api/conversation/session/{session_id}
```json
Response:
{
  "session_id": "abc123",
  "language": "en",
  "start_time": "2025-01-15T10:30:00Z",
  "message_count": 12,
  "intents": {
    "ask_question": 5,
    "place_order": 3
  }
}
```

## Mobile Responsiveness

All components are mobile-first with responsive breakpoints:

- **Mobile** (< 768px): Single column, stacked layout
- **Tablet** (768px - 1024px): Two columns
- **Desktop** (> 1024px): Full three-column layout

Message bubbles:
- Mobile: max-width 85%
- Desktop: max-width 75%

## Accessibility

- Keyboard navigation support
- ARIA labels on interactive elements
- High contrast mode compatible
- Screen reader friendly message structure

## Performance

- Auto-scroll throttled with `smooth` behavior
- Message list virtualization ready (for >100 messages)
- Lazy loading of conversation history
- Optimistic UI updates (messages appear before API response)

## Next Steps

1. **Backend Implementation**: Implement `/api/chatbot` endpoint using RAG retrieval
2. **Testing**: Test with real backend API once implemented
3. **Analytics**: Track conversation metrics (session duration, intent distribution)
4. **Enhancements**: Add voice input, file upload support

## Migration from Legacy

To migrate existing order processing to chatbot mode:

**Before:**
```typescript
<OrderInputPanel onSubmit={handleOrder} isProcessing={loading} />
```

**After:**
```typescript
<OrderInputPanel mode="chatbot" />  // That's it!
```

The chatbot mode handles everything automatically, including API calls.

## Troubleshooting

### Issue: Citations not displaying
**Solution**: Ensure backend returns `citations` array in response

### Issue: Session ID not persisting
**Solution**: Check that backend returns same `session_id` in subsequent responses

### Issue: Language selector not working
**Solution**: Verify backend supports `language` parameter in request

### Issue: Typing indicator stuck
**Solution**: Ensure try/catch in handleSubmit has `finally { setIsTyping(false) }`

## File Structure

```
frontend/
├── elements/
│   ├── OrderInputPanel.tsx      # Enhanced with chatbot mode
│   ├── ConversationPanel.tsx    # New conversation history viewer
│   ├── api-client.ts            # API functions for chatbot
│   └── types.ts                 # TypeScript types
└── CHATBOT_USAGE.md             # This file
```

## License

Part of TRIA AI-BPO Platform - Production-ready intelligent chatbot interface.
