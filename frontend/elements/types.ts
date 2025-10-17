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
