export type AgentId = 'customer-service' | 'orchestrator' | 'inventory' | 'delivery' | 'finance';

export type AgentStatusType = 'idle' | 'processing' | 'completed' | 'error';

export interface AgentStatus {
  id: AgentId;
  name: string;
  status: AgentStatusType;
  progress: number;
  tasks: string[];
  details?: string[];  // Array of real data points from backend
  current_task?: string;  // Current task description
  start_time?: number;
  end_time?: number;
}

export interface OrderResult {
  success: boolean;
  orderId: string;
  deliveryOrderId: string;
  invoiceId: string;
  totalBoxes: number;
  estimatedTotal: string;
  deliveryDate: string;
  outlet: string;
}

export interface OutletData {
  id: number;
  name: string;
  address: string;
  contact_person: string;
  phone: string;
}

// ============================================================
// CONVERSATIONAL AI TYPES
// ============================================================

export type ChatMode = 'order' | 'query' | 'status';

export type MessageIntent = 'place_order' | 'ask_question' | 'check_status' | 'general_inquiry' | 'unknown';

export type MessageType = 'text' | 'order_confirmation' | 'error' | 'typing' | 'system';

export interface RAGCitation {
  policy_id: string;
  policy_name: string;
  section: string;
  relevance_score: number;
  content?: string;  // Actual policy content excerpt
}

export interface ConversationalMessage {
  id: number;
  session_id?: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
  intent?: MessageIntent;
  confidence?: number;
  language?: string;
  citations?: RAGCitation[];
  mode?: ChatMode;
  type?: MessageType;
  metadata?: Record<string, any>;
}

export interface RAGResponse {
  answer: string;
  confidence: number;
  citations: RAGCitation[];
  language: string;
  intent: MessageIntent;
}

export interface ConversationSession {
  session_id: string;
  user_id?: string;
  outlet_id?: number;
  language: string;
  start_time: string;
  end_time?: string;
  message_count: number;
  intents: Record<string, number>;
  context: Record<string, any>;
}

export interface ConversationHistory {
  sessions: ConversationSession[];
  total_sessions: number;
  messages?: ConversationalMessage[];  // Messages for specific session
}

export interface ChatbotRequest {
  message: string;
  session_id?: string;
  outlet_name?: string;
  mode?: ChatMode;
  language?: string;
}

export interface ChatbotResponse {
  success: boolean;
  session_id: string;
  message: string;
  intent: MessageIntent;
  confidence: number;
  language: string;
  citations?: RAGCitation[];
  mode: ChatMode;
  metadata?: Record<string, any>;
  agent_timeline?: AgentStatus[];  // For order processing workflow visualization
  order_id?: number;  // When an order is created
  context?: Record<string, any>;
  error?: string;
}

// Language codes
export type LanguageCode = 'en' | 'zh' | 'ms';

export interface LanguageInfo {
  code: LanguageCode;
  name: string;
  flag: string;
}
