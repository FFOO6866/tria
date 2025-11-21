'use client';

import { useState } from 'react';
import OrderInputPanel from './OrderInputPanel';
import AgentActivityPanel from './AgentActivityPanel';
import OutputsPanel from './OutputsPanel';
import { OrderResult, AgentStatus, AgentId } from './types';
import { processOrder, ProcessOrderRequest } from './api-client';

export default function DemoLayout() {
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { id: 'customer-service', name: 'Customer Service', status: 'idle', progress: 0, tasks: [] },
    { id: 'orchestrator', name: 'Operations Orchestrator', status: 'idle', progress: 0, tasks: [] },
    { id: 'inventory', name: 'Inventory Manager', status: 'idle', progress: 0, tasks: [] },
    { id: 'delivery', name: 'Delivery Coordinator', status: 'idle', progress: 0, tasks: [] },
    { id: 'finance', name: 'Finance Controller', status: 'idle', progress: 0, tasks: [] },
  ]);

  const [orderResult, setOrderResult] = useState<OrderResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Handler for agent timeline updates from chatbot mode
  const handleAgentTimeline = (timeline: any[]) => {
    if (!timeline || timeline.length === 0) return;

    // Map backend agent names to frontend IDs
    const agentNameToId: Record<string, string> = {
      '🎧 Customer Service': 'customer-service',
      '🎯 Operations Orchestrator': 'orchestrator',
      '💰 Finance Controller': 'finance',
      '📦 Inventory Manager': 'inventory',
      '🚚 Delivery Coordinator': 'delivery',
    };

    // Update agents with real data from backend
    const updatedAgents: AgentStatus[] = timeline.map((backendAgent) => {
      const agentId = agentNameToId[backendAgent.agent_name] || 'customer-service';

      return {
        id: agentId as any,
        name: backendAgent.agent_name,
        status: backendAgent.status as any,
        progress: backendAgent.progress,
        tasks: [],
        details: backendAgent.details,
        current_task: backendAgent.current_task,
        start_time: backendAgent.start_time,
        end_time: backendAgent.end_time,
      };
    });

    // Fill in any missing agents as idle
    const allAgentIds: AgentId[] = ['customer-service', 'orchestrator', 'finance', 'inventory', 'delivery'];
    const processedIds = new Set(updatedAgents.map(a => a.id));

    allAgentIds.forEach(id => {
      if (!processedIds.has(id)) {
        const agentNames: Record<string, string> = {
          'customer-service': '🎧 Customer Service',
          'orchestrator': '🎯 Operations Orchestrator',
          'finance': '💰 Finance Controller',
          'inventory': '📦 Inventory Manager',
          'delivery': '🚚 Delivery Coordinator',
        };

        updatedAgents.push({
          id: id,
          name: agentNames[id],
          status: 'idle',
          progress: 0,
          tasks: [],
        });
      }
    });

    // Sort by agent order
    const agentOrder: AgentId[] = ['customer-service', 'orchestrator', 'finance', 'inventory', 'delivery'];
    updatedAgents.sort((a, b) => agentOrder.indexOf(a.id) - agentOrder.indexOf(b.id));

    setAgentStatuses(updatedAgents);
  };

  const handleOrderSubmit = async (message: string, outletName: string): Promise<void> => {
    setIsProcessing(true);
    setOrderResult(null);

    // Reset all agents to idle
    setAgentStatuses([
      { id: 'customer-service', name: 'Customer Service Agent', status: 'idle', progress: 0, tasks: [] },
      { id: 'orchestrator', name: 'Operations Orchestrator', status: 'idle', progress: 0, tasks: [] },
      { id: 'inventory', name: 'Inventory Manager', status: 'idle', progress: 0, tasks: [] },
      { id: 'delivery', name: 'Delivery Coordinator', status: 'idle', progress: 0, tasks: [] },
      { id: 'finance', name: 'Finance Controller', status: 'idle', progress: 0, tasks: [] },
    ]);

    try {
      // Call real API
      const request: ProcessOrderRequest = {
        whatsapp_message: message,
        outlet_name: outletName || undefined,
      };

      const response = await processOrder(request);

      // Send agent response to chat
      if ((window as any).__addAgentResponse) {
        const customerServiceAgent = response.agent_timeline.find(
          a => a.agent_name === 'Customer Service Agent'
        );

        if (customerServiceAgent && customerServiceAgent.details) {
          // Build a friendly response message
          let agentMessage = '✅ Order received and processed!\n\n';

          if (response.details?.parsed_order) {
            const parsed = response.details.parsed_order;
            agentMessage += `📋 Order Summary:\n`;
            agentMessage += `• Outlet: ${parsed.outlet_name || outletName}\n`;

            if (parsed.line_items && parsed.line_items.length > 0) {
              agentMessage += `• Items: ${parsed.line_items.length} product(s)\n`;
              parsed.line_items.forEach((item: any, idx: number) => {
                agentMessage += `  ${idx + 1}. ${item.quantity || 0}x ${item.description || item.sku}\n`;
              });
            }

            if (response.details.total_boxes) {
              agentMessage += `\n📦 Total: ${response.details.total_boxes} boxes\n`;
            }

            if (response.details.total) {
              agentMessage += `💰 Amount: $${response.details.total.toFixed(2)}\n`;
            }
          }

          agentMessage += '\n🤖 All agents are now coordinating to fulfill your order!';

          (window as any).__addAgentResponse(agentMessage);
        } else if (response.message) {
          (window as any).__addAgentResponse(response.message);
        }
      }

      // Map backend agent names to frontend agent IDs
      const agentNameToId: Record<string, string> = {
        'Customer Service Agent': 'customer-service',
        'Operations Orchestrator': 'orchestrator',
        'Inventory Manager': 'inventory',
        'Delivery Coordinator': 'delivery',
        'Finance Controller': 'finance',
      };

      // Update agents with real data from backend
      const updatedAgents: AgentStatus[] = response.agent_timeline.map((backendAgent) => {
        const agentId = agentNameToId[backendAgent.agent_name] || 'customer-service';

        return {
          id: agentId as any,
          name: backendAgent.agent_name,
          status: backendAgent.status as any,
          progress: backendAgent.progress,
          tasks: [],  // Use details instead
          details: backendAgent.details,
          current_task: backendAgent.current_task,
          start_time: backendAgent.start_time,
          end_time: backendAgent.end_time,
        };
      });

      // Fill in any missing agents as idle
      const allAgentIds: AgentId[] = ['customer-service', 'orchestrator', 'inventory', 'delivery', 'finance'];
      const processedIds = new Set(updatedAgents.map(a => a.id));

      allAgentIds.forEach(id => {
        if (!processedIds.has(id)) {
          const agentNames: Record<string, string> = {
            'customer-service': 'Customer Service Agent',
            'orchestrator': 'Operations Orchestrator',
            'inventory': 'Inventory Manager',
            'delivery': 'Delivery Coordinator',
            'finance': 'Finance Controller',
          };

          updatedAgents.push({
            id: id,
            name: agentNames[id],
            status: 'idle',
            progress: 0,
            tasks: [],
          });
        }
      });

      // Sort by agent order
      const agentOrder: AgentId[] = ['customer-service', 'orchestrator', 'inventory', 'delivery', 'finance'];
      updatedAgents.sort((a, b) => agentOrder.indexOf(a.id) - agentOrder.indexOf(b.id));

      setAgentStatuses(updatedAgents);

      // Extract order results from response details
      if (response.details) {
        const parsed = response.details.parsed_order || {};
        const totalBoxes = response.details.total_boxes || 0;
        const total = response.details.total || 0;

        setOrderResult({
          success: response.success,
          orderId: response.order_id?.toString() || 'ORD-' + Date.now(),
          deliveryOrderId: 'DO-' + new Date().toISOString().split('T')[0] + '-001',
          invoiceId: 'INV-' + new Date().toISOString().split('T')[0] + '-001',
          totalBoxes: totalBoxes,
          estimatedTotal: total.toFixed(2),
          deliveryDate: 'Tomorrow, 09:00 - 12:00',
          outlet: parsed.outlet_name || outletName || 'Unknown Outlet',
        });
      }

    } catch (error) {
      console.error('Order processing failed:', error);

      // Send error to chat
      if ((window as any).__addAgentResponse) {
        const errorMsg = `❌ Sorry, I encountered an error while processing your order:\n\n${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease try again or contact support.`;
        (window as any).__addAgentResponse(errorMsg);
      }

      // Mark all agents as error
      setAgentStatuses((prev) =>
        prev.map((agent) => ({
          ...agent,
          status: 'error',
          details: [`Error: ${error instanceof Error ? error.message : 'Unknown error'}`],
        }))
      );

      // Show error in output
      setOrderResult({
        success: false,
        orderId: 'ERROR',
        deliveryOrderId: '',
        invoiceId: '',
        totalBoxes: 0,
        estimatedTotal: '0.00',
        deliveryDate: '',
        outlet: '',
      });
    } finally {
      setIsProcessing(false);
    }
  };


  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/tria-logo.png"
                alt="TRIA Logo"
                className="w-12 h-12"
              />
              <div>
                <h1 className="text-2xl font-bold text-slate-900">TRIA AI-BPO Platform</h1>
                <p className="text-sm text-slate-500">Multi-Agent Supply Chain Automation</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm text-slate-600">
                <span className="font-semibold">Status:</span>{' '}
                <span className={isProcessing ? 'text-primary-600' : 'text-green-600'}>
                  {isProcessing ? 'Processing Order...' : 'Ready'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main 3-Column Layout */}
      <div className="max-w-[1920px] mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
          {/* Left Column: Order Input */}
          <div className="lg:col-span-1">
            <OrderInputPanel
              onSubmit={handleOrderSubmit}
              isProcessing={isProcessing}
              onAgentTimeline={handleAgentTimeline}
            />
          </div>

          {/* Middle Column: Agent Activity */}
          <div className="lg:col-span-1">
            <AgentActivityPanel agents={agentStatuses} />
          </div>

          {/* Right Column: Outputs */}
          <div className="lg:col-span-1">
            <OutputsPanel result={orderResult} isProcessing={isProcessing} />
          </div>
        </div>
      </div>
    </div>
  );
}
