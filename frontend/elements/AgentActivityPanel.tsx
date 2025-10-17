'use client';

import { Users, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { AgentStatus } from './types';
import AgentCard from './AgentCard';

interface AgentActivityPanelProps {
  agents: AgentStatus[];
}

export default function AgentActivityPanel({ agents }: AgentActivityPanelProps) {
  const activeCount = agents.filter((a) => a.status === 'processing').length;
  const completedCount = agents.filter((a) => a.status === 'completed').length;
  const errorCount = agents.filter((a) => a.status === 'error').length;

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-semibold text-slate-900">Agent Activity</h2>
          </div>
          <div className="flex items-center gap-3 text-sm">
            {activeCount > 0 && (
              <div className="flex items-center gap-1 text-primary-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="font-semibold">{activeCount}</span>
              </div>
            )}
            {completedCount > 0 && (
              <div className="flex items-center gap-1 text-green-600">
                <CheckCircle2 className="w-4 h-4" />
                <span className="font-semibold">{completedCount}</span>
              </div>
            )}
            {errorCount > 0 && (
              <div className="flex items-center gap-1 text-red-600">
                <AlertCircle className="w-4 h-4" />
                <span className="font-semibold">{errorCount}</span>
              </div>
            )}
          </div>
        </div>
        <p className="text-sm text-slate-500 mt-1">Real-time coordination across 5 AI agents</p>
      </div>

      <div className="card-body flex-1 overflow-y-auto">
        <div className="space-y-4">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>

        {/* Legend */}
        <div className="mt-6 p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-xs font-semibold text-slate-600 mb-2">Agent Status Legend</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-slate-300" />
              <span className="text-slate-600">Idle</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary-500 animate-pulse" />
              <span className="text-slate-600">Processing</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-slate-600">Completed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-slate-600">Error</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
