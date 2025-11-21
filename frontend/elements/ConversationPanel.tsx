'use client';

import { useState, useEffect, useRef, ReactElement } from 'react';
import { Check, CheckCheck, AlertCircle, Info, FileText } from 'lucide-react';
import type { ConversationalMessage, RAGCitation, LanguageCode } from './types';

interface ConversationPanelProps {
  messages: ConversationalMessage[];
  sessionId?: string;
  isTyping?: boolean;
  onExportTranscript?: () => void;
}

/**
 * ConversationPanel Component
 *
 * Displays full conversation history with enhanced metadata:
 * - Message timestamps and read receipts
 * - Intent detection badges
 * - Confidence scores
 * - Language indicators
 * - RAG policy citations
 * - Different message types (text, order_confirmation, error, system)
 *
 * Features:
 * - WhatsApp-style message bubbles
 * - Auto-scroll to latest message
 * - Citation expandable sections
 * - Message metadata tooltips
 * - Mobile-responsive design
 */
export default function ConversationPanel({
  messages,
  sessionId,
  isTyping = false,
  onExportTranscript,
}: ConversationPanelProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Language flag mapping
  const languageFlags: Record<LanguageCode, string> = {
    en: '🇬🇧',
    zh: '🇨🇳',
    ms: '🇲🇾',
  };

  // Intent badge colors
  const intentColors: Record<string, { bg: string; text: string; label: string }> = {
    place_order: { bg: 'bg-green-100', text: 'text-green-800', label: '📦 Order' },
    ask_question: { bg: 'bg-blue-100', text: 'text-blue-800', label: '❓ Question' },
    check_status: { bg: 'bg-purple-100', text: 'text-purple-800', label: '📊 Status' },
    general_inquiry: { bg: 'bg-gray-100', text: 'text-gray-800', label: '💬 Inquiry' },
    unknown: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: '🤔 Unknown' },
  };

  // Message type icons
  const messageTypeIcons: Record<string, ReactElement> = {
    order_confirmation: <Check className="w-4 h-4 text-green-600" />,
    error: <AlertCircle className="w-4 h-4 text-red-600" />,
    system: <Info className="w-4 h-4 text-blue-600" />,
  };

  // Format confidence percentage
  const formatConfidence = (confidence?: number): string => {
    if (!confidence) return '';
    return `${Math.round(confidence * 100)}%`;
  };

  // Render citation card
  const renderCitation = (citation: RAGCitation) => (
    <div
      key={citation.policy_id}
      className="mt-2 p-2 bg-blue-50 border-l-4 border-blue-500 rounded text-xs"
    >
      <div className="flex items-start gap-2">
        <FileText className="w-3 h-3 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="font-semibold text-blue-900">{citation.policy_name}</div>
          <div className="text-blue-700 mt-0.5">
            {citation.section}
            {citation.relevance_score && (
              <span className="ml-2 text-blue-500">
                ({Math.round(citation.relevance_score * 100)}% relevant)
              </span>
            )}
          </div>
          {citation.content && (
            <div className="mt-1 text-blue-600 italic">&quot;{citation.content}&quot;</div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-3 shadow-md">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm">Conversation History</h3>
            {sessionId && (
              <p className="text-xs text-blue-100 mt-0.5">Session: {sessionId.slice(0, 8)}...</p>
            )}
          </div>
          {onExportTranscript && (
            <button
              onClick={onExportTranscript}
              className="px-3 py-1 bg-white/20 hover:bg-white/30 text-white text-xs rounded-full transition-colors"
            >
              Export
            </button>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#e5ddd5] bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cGF0dGVybiBpZD0icGF0dGVybiIgd2lkdGg9IjMwIiBoZWlnaHQ9IjMwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj4KICAgIDxjaXJjbGUgY3g9IjUiIGN5PSI1IiByPSIxIiBmaWxsPSIjZGRkIiBvcGFjaXR5PSIwLjEiLz4KICA8L3BhdHRlcm4+CiAgPHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNwYXR0ZXJuKSIvPgo8L3N2Zz4=')]">
        {messages.length === 0 ? (
          <div className="text-center text-slate-500 py-12">
            <Info className="w-12 h-12 mx-auto mb-3 text-slate-400" />
            <p className="text-sm">No messages yet</p>
            <p className="text-xs mt-1">Start a conversation to see messages here</p>
          </div>
        ) : (
          messages.map((msg) => {
            const isUser = msg.sender === 'user';
            const intentInfo = msg.intent ? intentColors[msg.intent] : null;

            return (
              <div
                key={msg.id}
                className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-lg shadow ${
                    isUser
                      ? 'bg-[#dcf8c6] text-slate-900'
                      : msg.type === 'error'
                      ? 'bg-red-50 text-red-900 border border-red-200'
                      : msg.type === 'system'
                      ? 'bg-gray-100 text-gray-800 border border-gray-300'
                      : 'bg-white text-slate-900'
                  }`}
                >
                  {/* Message Header (Bot only) */}
                  {!isUser && (msg.intent || msg.language || msg.type) && (
                    <div className="px-3 pt-2 pb-1 flex items-center gap-2 flex-wrap border-b border-slate-100">
                      {/* Intent Badge */}
                      {intentInfo && (
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${intentInfo.bg} ${intentInfo.text}`}
                        >
                          {intentInfo.label}
                        </span>
                      )}

                      {/* Language Indicator */}
                      {msg.language && (
                        <span className="text-xs text-slate-500">
                          {languageFlags[msg.language as LanguageCode] || '🌐'} {msg.language.toUpperCase()}
                        </span>
                      )}

                      {/* Confidence Score */}
                      {msg.confidence !== undefined && msg.confidence > 0 && (
                        <span className="text-xs text-slate-500">
                          {formatConfidence(msg.confidence)} confidence
                        </span>
                      )}

                      {/* Message Type Icon */}
                      {msg.type && messageTypeIcons[msg.type] && (
                        <span className="ml-auto">{messageTypeIcons[msg.type]}</span>
                      )}
                    </div>
                  )}

                  {/* Message Content */}
                  <div className="px-3 py-2">
                    <p className="text-sm whitespace-pre-wrap break-words">{msg.text}</p>

                    {/* Citations Section */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-slate-600 font-semibold mb-1">
                          📚 Answer based on:
                        </p>
                        {msg.citations.map(renderCitation)}
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
          })
        )}

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

      {/* Session Info Footer */}
      {messages.length > 0 && (
        <div className="bg-slate-50 border-t border-slate-200 px-4 py-2">
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
            {messages[0]?.timestamp && (
              <span>Started: {messages[0].timestamp}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
