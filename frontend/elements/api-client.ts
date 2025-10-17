/**
 * API Client for TRIA AI-BPO Backend
 *
 * Connects to FastAPI server at http://localhost:8001 (enhanced_api.py)
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface ProcessOrderRequest {
  whatsapp_message: string;
  outlet_name?: string;
}

export interface AgentStatus {
  agent_name: string;
  status: string;
  current_task: string;
  details: string[];
  progress: number;
  start_time?: number;
  end_time?: number;
}

export interface ProcessOrderResponse {
  success: boolean;
  order_id?: number;
  run_id?: string;
  message: string;
  agent_timeline: AgentStatus[];
  details?: Record<string, any>;
}

export interface Outlet {
  id: number;
  name: string;
  address: string;
  contact_person: string;
  phone: string;
}

/**
 * Process order through Customer Service Agent (Enhanced with real data)
 */
export async function processOrder(
  request: ProcessOrderRequest
): Promise<ProcessOrderResponse> {
  const response = await fetch(`${API_BASE_URL}/api/process_order_enhanced`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to process order');
  }

  return response.json();
}

/**
 * List all outlets from database
 */
export async function listOutlets(): Promise<Outlet[]> {
  const response = await fetch(`${API_BASE_URL}/api/outlets`);

  if (!response.ok) {
    throw new Error('Failed to fetch outlets');
  }

  const data = await response.json();
  return data.outlets || [];
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<{ status: string; database: string; runtime: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error('Health check failed');
  }

  return response.json();
}

/**
 * Download Delivery Order as Excel file
 */
export async function downloadDeliveryOrder(orderId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/download_do/${orderId}`);

  if (!response.ok) {
    throw new Error('Failed to download DO');
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `DO_${orderId}.xlsx`;

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }

  // Create blob and trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

/**
 * Download Invoice as PDF file
 */
export async function downloadInvoice(orderId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/download_invoice/${orderId}`);

  if (!response.ok) {
    throw new Error('Failed to download invoice');
  }

  // Get filename from Content-Disposition header or use default
  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = `Invoice_${orderId}.pdf`;

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
    if (filenameMatch) {
      filename = filenameMatch[1];
    }
  }

  // Create blob and trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

/**
 * Post invoice to Xero
 */
export async function postToXero(orderId: number): Promise<{
  success: boolean;
  message: string;
  details?: any;
}> {
  const response = await fetch(`${API_BASE_URL}/api/post_to_xero/${orderId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to post to Xero');
  }

  return response.json();
}
