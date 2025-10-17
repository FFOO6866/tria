'use client';

import { Bot, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { AgentStatus, AgentId } from './types';

interface AgentCardProps {
  agent: AgentStatus;
}

const agentColors: Record<AgentId, string> = {
  'customer-service': 'text-green-600 border-green-600 bg-green-50',
  'orchestrator': 'text-purple-600 border-purple-600 bg-purple-50',
  'inventory': 'text-amber-600 border-amber-600 bg-amber-50',
  'delivery': 'text-blue-600 border-blue-600 bg-blue-50',
  'finance': 'text-pink-600 border-pink-600 bg-pink-50',
};

const agentIcons: Record<AgentId, string> = {
  'customer-service': '🎧',
  'orchestrator': '🎯',
  'inventory': '📦',
  'delivery': '🚚',
  'finance': '💰',
};

export default function AgentCard({ agent }: AgentCardProps) {
  const isActive = agent.status === 'processing';
  const isCompleted = agent.status === 'completed';
  const isError = agent.status === 'error';
  const isIdle = agent.status === 'idle';

  const colorClass = agentColors[agent.id as AgentId];

  return (
    <div
      className={`agent-card ${agent.status} ${isActive ? colorClass : ''} transition-all duration-300`}
    >
      {/* Agent Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${
              isActive ? 'animate-pulse-slow' : ''
            } ${isCompleted ? 'bg-green-100' : isError ? 'bg-red-100' : 'bg-slate-100'}`}
          >
            {agentIcons[agent.id as AgentId]}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm">{agent.name}</h3>
            <p className="text-xs text-slate-500 capitalize">{agent.status}</p>
          </div>
        </div>

        {/* Status Icon */}
        <div>
          {isActive && <Loader2 className="w-5 h-5 text-current animate-spin" />}
          {isCompleted && <CheckCircle2 className="w-5 h-5 text-green-600" />}
          {isError && <AlertCircle className="w-5 h-5 text-red-600" />}
          {isIdle && <Bot className="w-5 h-5 text-slate-400" />}
        </div>
      </div>

      {/* Progress Bar */}
      {(isActive || isCompleted) && (
        <div className="mb-3">
          <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                isCompleted ? 'bg-green-500' : 'bg-current'
              }`}
              style={{ width: `${agent.progress}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1 text-right">{agent.progress}%</p>
        </div>
      )}

      {/* Current Task */}
      {agent.current_task && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-slate-700">{agent.current_task}</p>
        </div>
      )}

      {/* Details List - Real Data from Backend */}
      {agent.details && agent.details.length > 0 && (
        <div className="space-y-1.5">
          {agent.details.map((detail, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2 text-xs text-slate-700 animate-in fade-in slide-in-from-left-2 duration-300"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <span className="text-slate-400 mt-0.5">•</span>
              <span className="flex-1">{detail}</span>
              {idx === agent.details.length - 1 && isActive && (
                <Loader2 className="w-3 h-3 text-current animate-spin flex-shrink-0 mt-0.5" />
              )}
              {idx < agent.details.length - 1 && isCompleted && (
                <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0 mt-0.5" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Fallback: Task List (for backward compatibility) */}
      {(!agent.details || agent.details.length === 0) && agent.tasks.length > 0 && (
        <div className="space-y-1.5">
          {agent.tasks.map((task, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2 text-xs text-slate-700 animate-in fade-in slide-in-from-left-2 duration-300"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <span className="text-slate-400 mt-0.5">•</span>
              <span className="flex-1">{task}</span>
              {idx === agent.tasks.length - 1 && isActive && (
                <Loader2 className="w-3 h-3 text-current animate-spin flex-shrink-0 mt-0.5" />
              )}
              {idx < agent.tasks.length - 1 && (
                <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0 mt-0.5" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Idle State */}
      {isIdle && (
        <p className="text-xs text-slate-400 italic">Waiting for order...</p>
      )}
    </div>
  );
}
