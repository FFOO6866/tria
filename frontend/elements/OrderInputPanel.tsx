'use client';

import { useState, useEffect, useRef } from 'react';
import { Send, Phone, Video, MoreVertical, Check, CheckCheck, Globe } from 'lucide-react';
import type { ConversationalMessage, ChatbotRequest, LanguageCode } from './types';
import { sendChatbotMessage } from './api-client';

interface OrderInputPanelProps {
  onSubmit?: (message: string, outlet: string) => Promise<void>;
  isProcessing?: boolean;
  onAgentResponse?: (response: string) => void;
  onAgentTimeline?: (timeline: any[]) => void;  // For displaying agent activity
  mode?: 'chatbot' | 'order';  // 'chatbot' for intelligent Q&A, 'order' for legacy order processing
}

// Legacy interface for backward compatibility
interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
}

export default function OrderInputPanel({
  onSubmit,
  isProcessing = false,
  onAgentResponse,
  onAgentTimeline,
  mode = 'chatbot'
}: OrderInputPanelProps) {
  const [message, setMessage] = useState('');
  const [outlet, setOutlet] = useState('Canadian Pizza Pasir Ris');
  const [sessionId, setSessionId] = useState<string>('');
  const [language, setLanguage] = useState<LanguageCode>('en');
  const [chatHistory, setChatHistory] = useState<ConversationalMessage[]>([
    {
      id: 1,
      text: mode === 'chatbot'
        ? 'Hello! I\'m your AI assistant. Ask me about policies, place orders, or get help with anything.'
        : 'Hello! I\'m your AI order assistant. Send me your order and I\'ll process it for you.',
      sender: 'bot',
      timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      type: 'system',
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const sampleMessages = mode === 'chatbot'
    ? [
        {
          label: '❓ Policy',
          text: 'What is your return policy for damaged goods?',
        },
        {
          label: '📦 Order',
          text: 'I need 600 x 10" and 200 x 12" pizza boxes',
        },
        {
          label: '💰 Pricing',
          text: 'What are your bulk pricing options for monthly orders?',
        },
        {
          label: '🚚 Delivery',
          text: 'How long does delivery usually take?',
        },
      ]
    : [
        {
          label: '📦 Standard',
          text: 'Hi! Need 600 x 10", 200 x 12", and 400 x 14" boxes. Regular delivery is fine.',
        },
        {
          label: '⚡ Urgent',
          text: 'URGENT: Need 800 x 10" and 300 x 12" boxes ASAP! Running low on stock.',
        },
        {
          label: '📊 Large',
          text: 'Placing order: 1000 x 10", 500 x 12", 600 x 14" boxes. Standard delivery.',
        },
      ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing && !isTyping) {
      // Add user message to chat
      const userMessage: ConversationalMessage = {
        id: Date.now(),
        text: message,
        sender: 'user',
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        type: 'text',
      };
      setChatHistory((prev) => [...prev, userMessage]);

      // Clear input immediately for better UX
      const currentMessage = message;
      setMessage('');

      if (mode === 'chatbot') {
        // NEW: Intelligent chatbot mode with RAG and intent detection
        setIsTyping(true);

        try {
          const request: ChatbotRequest = {
            message: currentMessage,
            session_id: sessionId || undefined,
            outlet_name: outlet,
            language: language,
          };

          const response = await sendChatbotMessage(request);

          // Update session ID if new
          if (response.session_id && !sessionId) {
            setSessionId(response.session_id);
          }

          // Add bot response to chat
          const botMessage: ConversationalMessage = {
            id: Date.now() + 1,
            text: response.message,
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            intent: response.intent,
            confidence: response.confidence,
            language: response.language,
            citations: response.citations,
            mode: response.mode,
            type: response.success ? 'text' : 'error',
            session_id: response.session_id,
          };

          setChatHistory((prev) => [...prev, botMessage]);

          // Notify parent if provided
          if (onAgentResponse) {
            onAgentResponse(response.message);
          }

          // Pass agent timeline for activity visualization
          if (onAgentTimeline && response.agent_timeline) {
            onAgentTimeline(response.agent_timeline);
          }
        } catch (error) {
          // Add error message to chat
          const errorMessage: ConversationalMessage = {
            id: Date.now() + 1,
            text: `❌ Error: ${error instanceof Error ? error.message : 'Failed to send message'}`,
            sender: 'bot',
            timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            type: 'error',
          };
          setChatHistory((prev) => [...prev, errorMessage]);
        } finally {
          setIsTyping(false);
        }
      } else {
        // LEGACY: Order processing mode (backward compatibility)
        const processingMessage: ConversationalMessage = {
          id: Date.now() + 1,
          text: 'Processing your order... 🔄',
          sender: 'bot',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          type: 'system',
        };
        setChatHistory((prev) => [...prev, processingMessage]);

        try {
          if (onSubmit) {
            await onSubmit(currentMessage, outlet);
          }
        } catch (error) {
          // Error handling is done in parent component
        }
      }
    }
  };

  // Public method to add agent response to chat
  const addAgentResponse = (response: string) => {
    setChatHistory((prev) => {
      // Remove the "Processing..." message
      const filtered = prev.filter(msg => !msg.text.includes('Processing your order'));

      // Add agent response
      return [
        ...filtered,
        {
          id: Date.now(),
          text: response,
          sender: 'bot',
          timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        },
      ];
    });
  };

  // Expose addAgentResponse via ref (we'll use a different approach)
  // Instead, we'll listen for onAgentResponse callback
  if (onAgentResponse) {
    // This is a hack but works for demo purposes
    (window as any).__addAgentResponse = addAgentResponse;
  }

  const useSample = (text: string) => {
    setMessage(text);
  };

  return (
    <div className="h-full flex flex-col bg-[#e5ddd5] rounded-lg overflow-hidden shadow-lg">
      {/* WhatsApp Header */}
      <div className="bg-[#075e54] text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img
            src="/tria-logo.png"
            alt="TRIA Logo"
            className="w-10 h-10 rounded-full bg-white p-1"
          />
          <div className="flex-1">
            <h2 className="font-semibold text-sm">
              {mode === 'chatbot' ? 'TRIA AI Assistant' : 'TRIA AI Order Assistant'}
            </h2>
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={outlet}
                onChange={(e) => setOutlet(e.target.value)}
                className="text-xs bg-transparent border-none outline-none text-green-100 cursor-pointer"
                disabled={isProcessing || isTyping}
              >
                <option value="Canadian Pizza Pasir Ris" className="text-slate-800">Canadian Pizza Pasir Ris</option>
                <option value="Canadian Pizza Sembawang" className="text-slate-800">Canadian Pizza Sembawang</option>
                <option value="Canadian Pizza Serangoon" className="text-slate-800">Canadian Pizza Serangoon</option>
              </select>

              {/* Language Selector (Chatbot Mode Only) */}
              {mode === 'chatbot' && (
                <>
                  <span className="text-green-100">•</span>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as LanguageCode)}
                    className="text-xs bg-transparent border-none outline-none text-green-100 cursor-pointer"
                    disabled={isProcessing || isTyping}
                  >
                    <option value="en" className="text-slate-800">🇬🇧 English</option>
                    <option value="zh" className="text-slate-800">🇨🇳 中文</option>
                    <option value="ms" className="text-slate-800">🇲🇾 Bahasa</option>
                  </select>
                </>
              )}

              {/* Session ID Indicator */}
              {sessionId && (
                <>
                  <span className="text-green-100">•</span>
                  <span className="text-xs text-green-100" title={sessionId}>
                    Session: {sessionId.slice(0, 8)}...
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {mode === 'chatbot' && (
            <Globe className="w-5 h-5 cursor-pointer opacity-80 hover:opacity-100" title="Multi-language support" />
          )}
          <Video className="w-5 h-5 cursor-pointer opacity-80 hover:opacity-100" />
          <Phone className="w-5 h-5 cursor-pointer opacity-80 hover:opacity-100" />
          <MoreVertical className="w-5 h-5 cursor-pointer opacity-80 hover:opacity-100" />
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cGF0dGVybiBpZD0icGF0dGVybiIgd2lkdGg9IjMwIiBoZWlnaHQ9IjMwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgIDxjaXJjbGUgY3g9IjUiIGN5PSI1IiByPSIxIiBmaWxsPSIjZGRkIiBvcGFjaXR5PSIwLjEiLz4KICU8L3BhdHRlcm4+CiAgPHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNwYXR0ZXJuKSIvPgo8L3N2Zz4=')]">
        {chatHistory.map((msg) => {
          const isUser = msg.sender === 'user';
          const isError = msg.type === 'error';

          // Intent badge configuration
          const intentBadges: Record<string, { emoji: string; label: string; color: string }> = {
            place_order: { emoji: '📦', label: 'Order', color: 'bg-green-100 text-green-800' },
            ask_question: { emoji: '❓', label: 'Question', color: 'bg-blue-100 text-blue-800' },
            check_status: { emoji: '📊', label: 'Status', color: 'bg-purple-100 text-purple-800' },
            general_inquiry: { emoji: '💬', label: 'Inquiry', color: 'bg-gray-100 text-gray-800' },
          };

          const intentBadge = msg.intent ? intentBadges[msg.intent] : null;

          return (
            <div
              key={msg.id}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-lg shadow ${
                  isUser
                    ? 'bg-[#dcf8c6] text-slate-900'
                    : isError
                    ? 'bg-red-50 text-red-900 border border-red-200'
                    : 'bg-white text-slate-900'
                }`}
              >
                {/* Bot Message Header (Intent, Language, Confidence) */}
                {!isUser && mode === 'chatbot' && (msg.intent || msg.language || msg.confidence) && (
                  <div className="px-3 pt-2 pb-1 flex items-center gap-2 flex-wrap text-xs border-b border-slate-100">
                    {/* Intent Badge */}
                    {intentBadge && (
                      <span className={`px-2 py-0.5 rounded-full font-medium ${intentBadge.color}`}>
                        {intentBadge.emoji} {intentBadge.label}
                      </span>
                    )}

                    {/* Language Indicator */}
                    {msg.language && msg.language !== 'en' && (
                      <span className="text-slate-600">
                        {msg.language === 'zh' && '🇨🇳'}
                        {msg.language === 'ms' && '🇲🇾'}
                        {' '}{msg.language.toUpperCase()}
                      </span>
                    )}

                    {/* Confidence Score */}
                    {msg.confidence !== undefined && msg.confidence > 0 && (
                      <span className="text-slate-500">
                        {Math.round(msg.confidence * 100)}% confident
                      </span>
                    )}
                  </div>
                )}

                {/* Message Content */}
                <div className="px-3 py-2">
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.text}</p>

                  {/* RAG Citations */}
                  {mode === 'chatbot' && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-xs font-semibold text-blue-700">📚 Based on:</p>
                      {msg.citations.map((citation, idx) => (
                        <div
                          key={idx}
                          className="p-2 bg-blue-50 border-l-4 border-blue-400 rounded text-xs"
                        >
                          <div className="font-semibold text-blue-900">{citation.policy_name}</div>
                          <div className="text-blue-700 mt-0.5">{citation.section}</div>
                          {citation.relevance_score && (
                            <div className="text-blue-600 text-[10px] mt-1">
                              {Math.round(citation.relevance_score * 100)}% relevant
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Message Footer */}
                <div className="px-3 pb-2 flex items-center justify-end gap-1">
                  <span className="text-[10px] text-slate-500">{msg.timestamp}</span>
                  {isUser && (
                    <CheckCheck className="w-3 h-3 text-blue-500" />
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-white rounded-lg px-4 py-3 shadow">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        {/* Invisible div for auto-scroll */}
        <div ref={chatEndRef} />
      </div>

      {/* Quick Reply Buttons */}
      {!isProcessing && !isTyping && (
        <div className="px-4 py-2 bg-white border-t border-slate-200">
          <p className="text-[10px] text-slate-500 mb-2">Quick replies:</p>
          <div className="flex gap-2 flex-wrap">
            {sampleMessages.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => useSample(sample.text)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs rounded-full border border-slate-300 transition-colors"
              >
                {sample.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message Input */}
      <form onSubmit={handleSubmit} className="bg-[#f0f0f0] px-4 py-3 flex items-center gap-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={
            mode === 'chatbot'
              ? 'Ask a question or place an order...'
              : 'Type a message'
          }
          className="flex-1 px-4 py-2 bg-white rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-[#25d366]"
          disabled={isProcessing || isTyping}
        />
        <button
          type="submit"
          disabled={isProcessing || isTyping || !message.trim()}
          className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
            isProcessing || isTyping || !message.trim()
              ? 'bg-slate-300 cursor-not-allowed'
              : 'bg-[#25d366] hover:bg-[#20bd5a] cursor-pointer'
          }`}
        >
          {isProcessing || isTyping ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Send className="w-5 h-5 text-white" />
          )}
        </button>
      </form>
    </div>
  );
}
