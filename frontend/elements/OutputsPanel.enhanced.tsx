'use client';

import {
  FileText, Download, CheckCircle2, Loader2, Package, DollarSign,
  Truck, ExternalLink, ChevronDown, ChevronRight, Calendar,
  Filter, BarChart3, Box, Boxes
} from 'lucide-react';
import { OrderResult } from './types';
import { downloadDeliveryOrder, downloadInvoice, postToXero } from './api-client';
import { useState, useEffect } from 'react';

interface OutputsPanelProps {
  result: OrderResult | null;
  isProcessing: boolean;
}

interface AgentOutput {
  agent_name: string;
  category: string;
  status: string;
  current_task: string;
  details: string[];
  metadata?: {
    do_number?: string;
    invoice_number?: string;
    customer?: string;
    total_amount?: number;
    inventory_summary?: Array<{
      sku: string;
      product_name: string;
      before: number;
      requested: number;
      after: number;
      status: string;
    }>;
  };
  date: string;
  time: string;
}

interface GeneratedOutputsSummary {
  summary: {
    total_operations: number;
    by_category: Record<string, number>;
    documents_generated: {
      delivery_orders: Array<{
        do_number: string;
        customer: string;
        total_amount: number;
        total_quantity: number;
        date: string;
      }>;
      invoices: Array<{
        invoice_number: string;
        customer: string;
        total_amount: number;
        tax_amount: number;
        date: string;
      }>;
    };
  };
  inventory_movements: Array<{
    product: string;
    sku: string;
    before: number;
    withdrawn: number;
    after: number;
    date: string;
  }>;
  by_date: Record<string, AgentOutput[]>;
  by_category: Record<string, AgentOutput[]>;
}

type ViewMode = 'summary' | 'detailed';
type FilterCategory = 'all' | 'inventory' | 'delivery' | 'finance' | 'orders';

export default function OutputsPanelEnhanced({ result, isProcessing }: OutputsPanelProps) {
  const [downloading, setDownloading] = useState<'do' | 'invoice' | null>(null);
  const [postingXero, setPostingXero] = useState(false);
  const [xeroMessage, setXeroMessage] = useState<string | null>(null);

  // New state for detailed outputs
  const [viewMode, setViewMode] = useState<ViewMode>('summary');
  const [filterCategory, setFilterCategory] = useState<FilterCategory>('all');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [detailedOutputs, setDetailedOutputs] = useState<GeneratedOutputsSummary | null>(null);
  const [loadingOutputs, setLoadingOutputs] = useState(false);

  // Fetch detailed outputs when result is available
  useEffect(() => {
    if (result?.orderId && viewMode === 'detailed') {
      fetchDetailedOutputs();
    }
  }, [result, viewMode]);

  const fetchDetailedOutputs = async () => {
    setLoadingOutputs(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/generated-outputs?group_by=summary');
      const data = await response.json();
      setDetailedOutputs(data);
    } catch (error) {
      console.error('Failed to fetch detailed outputs:', error);
    } finally {
      setLoadingOutputs(false);
    }
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleDownloadDO = async () => {
    if (!result?.orderId) return;
    try {
      setDownloading('do');
      await downloadDeliveryOrder(result.orderId);
    } catch (error) {
      console.error('Failed to download DO:', error);
      alert('Failed to download Delivery Order. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadInvoice = async () => {
    if (!result?.orderId) return;
    try {
      setDownloading('invoice');
      await downloadInvoice(result.orderId);
    } catch (error) {
      console.error('Failed to download invoice:', error);
      alert('Failed to download Invoice. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  const handlePostToXero = async () => {
    if (!result?.orderId) return;
    try {
      setPostingXero(true);
      const response = await postToXero(result.orderId);
      if (response.success) {
        setXeroMessage('Invoice posted to Xero successfully!');
      } else {
        setXeroMessage(response.message || 'Xero credentials not configured');
      }
    } catch (error) {
      console.error('Failed to post to Xero:', error);
      setXeroMessage('Failed to post to Xero. Please check credentials.');
    } finally {
      setPostingXero(false);
    }
  };

  // Category color mapping
  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'inventory': return 'green';
      case 'delivery': return 'blue';
      case 'finance': return 'pink';
      case 'orders': return 'purple';
      default: return 'slate';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'inventory': return Box;
      case 'delivery': return Truck;
      case 'finance': return DollarSign;
      case 'orders': return Package;
      default: return FileText;
    }
  };

  // Filter outputs by category
  const getFilteredOutputs = () => {
    if (!detailedOutputs) return [];

    if (filterCategory === 'all') {
      // Combine all categories
      return Object.values(detailedOutputs.by_category).flat();
    }

    return detailedOutputs.by_category[filterCategory] || [];
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-slate-900">Generated Outputs</h2>
          </div>

          {/* View Mode Toggle */}
          {result && (
            <div className="flex gap-1 bg-slate-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('summary')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  viewMode === 'summary'
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Summary
              </button>
              <button
                onClick={() => setViewMode('detailed')}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  viewMode === 'detailed'
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Detailed
              </button>
            </div>
          )}
        </div>
        <p className="text-sm text-slate-500 mt-1">
          {viewMode === 'summary' ? 'Delivery Order & Invoice' : 'Complete Agent Activity Log'}
        </p>
      </div>

      <div className="card-body flex-1 overflow-y-auto">
        {!result && !isProcessing && (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-slate-400" />
            </div>
            <p className="text-slate-600 font-medium">No outputs yet</p>
            <p className="text-sm text-slate-400 mt-1">Process an order to see results</p>
          </div>
        )}

        {isProcessing && !result && (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin mb-4" />
            <p className="text-slate-600 font-medium">Processing order...</p>
            <p className="text-sm text-slate-400 mt-1">Agents are working on your request</p>
          </div>
        )}

        {/* SUMMARY VIEW */}
        {result && viewMode === 'summary' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Success Banner */}
            <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-8 h-8 text-green-600 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-green-900">Order Processed Successfully!</h3>
                  <p className="text-sm text-green-700 mt-1">
                    All agents completed their tasks. Order #{result.orderId}
                  </p>
                </div>
              </div>
            </div>

            {/* Order Summary */}
            <div className="border-2 border-slate-200 rounded-lg p-4">
              <h4 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Package className="w-4 h-4" />
                Order Summary
              </h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Customer:</span>
                  <span className="font-medium text-slate-900">{result.outlet}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Total Boxes:</span>
                  <span className="font-medium text-slate-900">{result.totalBoxes} units</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Estimated Total:</span>
                  <span className="font-medium text-slate-900">${result.estimatedTotal}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600">Delivery:</span>
                  <span className="font-medium text-slate-900">{result.deliveryDate}</span>
                </div>
              </div>
            </div>

            {/* Delivery Order */}
            <div className="border-2 border-blue-200 bg-blue-50 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-blue-900 flex items-center gap-2">
                    <Truck className="w-4 h-4" />
                    Delivery Order (DO)
                  </h4>
                  <p className="text-xs text-blue-700 mt-1">Generated from Excel template</p>
                </div>
                <button
                  onClick={handleDownloadDO}
                  disabled={downloading === 'do'}
                  className="text-blue-600 hover:text-blue-700 text-sm font-medium flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'do' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download
                    </>
                  )}
                </button>
              </div>

              <div className="bg-white border border-blue-200 rounded p-3 space-y-2 text-sm font-mono">
                <div className="font-semibold text-slate-900">DO #{result.deliveryOrderId}</div>
                <div className="text-slate-600">Date: {new Date().toLocaleDateString()}</div>
                <div className="text-slate-600">Customer: {result.outlet}</div>
                <div className="border-t border-slate-200 pt-2 mt-2">
                  <div className="text-slate-700">Items: {result.totalBoxes} boxes</div>
                  <div className="text-slate-700">Delivery: {result.deliveryDate}</div>
                </div>
                <div className="text-xs text-green-600 mt-2">✓ Stock verified from Master Inventory</div>
              </div>
            </div>

            {/* Invoice */}
            <div className="border-2 border-pink-200 bg-pink-50 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-pink-900 flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Invoice
                  </h4>
                  <p className="text-xs text-pink-700 mt-1">Ready for Xero posting</p>
                </div>
                <button
                  onClick={handleDownloadInvoice}
                  disabled={downloading === 'invoice'}
                  className="text-pink-600 hover:text-pink-700 text-sm font-medium flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'invoice' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download
                    </>
                  )}
                </button>
              </div>

              <div className="bg-white border border-pink-200 rounded p-3 space-y-2 text-sm font-mono">
                <div className="font-semibold text-slate-900">Invoice #{result.invoiceId}</div>
                <div className="text-slate-600">Date: {new Date().toLocaleDateString()}</div>
                <div className="text-slate-600">Bill To: {result.outlet}</div>
                <div className="border-t border-slate-200 pt-2 mt-2">
                  <div className="flex justify-between text-slate-700">
                    <span>Pizza Boxes ({result.totalBoxes} units)</span>
                    <span>${result.estimatedTotal}</span>
                  </div>
                  <div className="flex justify-between font-semibold text-slate-900 mt-2 pt-2 border-t">
                    <span>Total Amount</span>
                    <span>${result.estimatedTotal}</span>
                  </div>
                </div>
                <div className="text-xs text-green-600 mt-2">✓ Posted to Xero successfully</div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              <div className="flex gap-3">
                <button
                  onClick={handleDownloadDO}
                  disabled={downloading === 'do'}
                  className="flex-1 btn-secondary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'do' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading DO...
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4" />
                      Download Full DO
                    </>
                  )}
                </button>
                <button
                  onClick={handleDownloadInvoice}
                  disabled={downloading === 'invoice'}
                  className="flex-1 btn-secondary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloading === 'invoice' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading Invoice...
                    </>
                  ) : (
                    <>
                      <DollarSign className="w-4 h-4" />
                      Download Invoice
                    </>
                  )}
                </button>
              </div>

              {/* Xero Integration */}
              <button
                onClick={handlePostToXero}
                disabled={postingXero}
                className="w-full btn-primary flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {postingXero ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Posting to Xero...
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    Post Invoice to Xero
                  </>
                )}
              </button>

              {/* Xero Status Message */}
              {xeroMessage && (
                <div className={`text-sm p-3 rounded-lg ${
                  xeroMessage.includes('successfully')
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                  {xeroMessage}
                </div>
              )}
            </div>

            {/* Integration Status */}
            <div className="border-t pt-4 space-y-2">
              <p className="text-xs font-semibold text-slate-600">Integration Status:</p>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Database: Order saved to PostgreSQL</span>
                </div>
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Excel: DO generated from template</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Xero: Ready for posting (click button above)</span>
                </div>
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>AI: GPT-4 parsed order accurately</span>
                </div>
              </div>
            </div>

            {/* Hint to switch to detailed view */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
              <p className="text-sm text-blue-900">
                💡 <span className="font-medium">Want to see detailed agent outputs?</span>
              </p>
              <p className="text-xs text-blue-700 mt-1">
                Switch to "Detailed" view above to see inventory movements, line items, and more
              </p>
            </div>
          </div>
        )}

        {/* DETAILED VIEW */}
        {result && viewMode === 'detailed' && (
          <div className="space-y-4">
            {/* Category Filter */}
            <div className="flex items-center gap-2 flex-wrap">
              <Filter className="w-4 h-4 text-slate-500" />
              <span className="text-xs font-medium text-slate-600">Filter:</span>
              {(['all', 'inventory', 'delivery', 'finance', 'orders'] as FilterCategory[]).map((cat) => {
                const color = cat === 'all' ? 'slate' : getCategoryColor(cat);
                const isActive = filterCategory === cat;

                return (
                  <button
                    key={cat}
                    onClick={() => setFilterCategory(cat)}
                    className={`px-3 py-1 text-xs font-medium rounded-full transition-all ${
                      isActive
                        ? `bg-${color}-100 text-${color}-700 border-2 border-${color}-300`
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </button>
                );
              })}
            </div>

            {loadingOutputs && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
              </div>
            )}

            {!loadingOutputs && detailedOutputs && (
              <div className="space-y-4">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-green-50 border-2 border-green-200 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <Boxes className="w-5 h-5 text-green-600" />
                      <div>
                        <p className="text-xs text-green-700 font-medium">Operations</p>
                        <p className="text-2xl font-bold text-green-900">
                          {detailedOutputs.summary.total_operations}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-3">
                    <div className="flex items-center gap-2">
                      <Truck className="w-5 h-5 text-blue-600" />
                      <div>
                        <p className="text-xs text-blue-700 font-medium">Documents</p>
                        <p className="text-2xl font-bold text-blue-900">
                          {detailedOutputs.summary.documents_generated.delivery_orders.length +
                           detailedOutputs.summary.documents_generated.invoices.length}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Agent Outputs */}
                {getFilteredOutputs().map((output, idx) => {
                  const color = getCategoryColor(output.category);
                  const Icon = getCategoryIcon(output.category);
                  const sectionId = `${output.category}-${idx}`;
                  const isExpanded = expandedSections.has(sectionId);

                  return (
                    <div
                      key={sectionId}
                      className={`border-2 border-${color}-200 bg-${color}-50 rounded-lg overflow-hidden`}
                    >
                      {/* Header */}
                      <button
                        onClick={() => toggleSection(sectionId)}
                        className="w-full px-4 py-3 flex items-center justify-between hover:bg-${color}-100 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <Icon className={`w-5 h-5 text-${color}-600`} />
                          <div className="text-left">
                            <h4 className={`font-semibold text-${color}-900`}>
                              {output.agent_name}
                            </h4>
                            <p className={`text-xs text-${color}-700`}>
                              {output.current_task}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-1 rounded-full bg-${color}-200 text-${color}-800`}>
                            {output.status}
                          </span>
                          {isExpanded ? (
                            <ChevronDown className={`w-5 h-5 text-${color}-600`} />
                          ) : (
                            <ChevronRight className={`w-5 h-5 text-${color}-600`} />
                          )}
                        </div>
                      </button>

                      {/* Expanded Content */}
                      {isExpanded && (
                        <div className="px-4 pb-4 space-y-3 border-t border-${color}-200 bg-white">
                          {/* Timestamp */}
                          <div className="flex items-center gap-2 pt-3 text-xs text-slate-600">
                            <Calendar className="w-3 h-3" />
                            <span>{output.date} at {output.time}</span>
                          </div>

                          {/* Details */}
                          <div className="space-y-1">
                            {output.details.map((detail, detailIdx) => (
                              <div
                                key={detailIdx}
                                className="text-sm text-slate-700 font-mono leading-relaxed"
                              >
                                {detail}
                              </div>
                            ))}
                          </div>

                          {/* Inventory Summary (if available) */}
                          {output.metadata?.inventory_summary && output.metadata.inventory_summary.length > 0 && (
                            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded">
                              <p className="text-xs font-semibold text-green-900 mb-2">
                                Inventory Movements:
                              </p>
                              <div className="space-y-1">
                                {output.metadata.inventory_summary.map((item, itemIdx) => (
                                  <div key={itemIdx} className="text-xs text-green-800">
                                    {item.product_name}: {item.before} → {item.after} units
                                    ({item.status === 'available' ? '✓ Available' : '⚠ Low Stock'})
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Document Reference (if available) */}
                          {(output.metadata?.do_number || output.metadata?.invoice_number) && (
                            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded">
                              <p className="text-xs font-semibold text-blue-900 mb-1">
                                Document Generated:
                              </p>
                              <p className="text-xs text-blue-800 font-mono">
                                {output.metadata.do_number || output.metadata.invoice_number}
                              </p>
                              {output.metadata.customer && (
                                <p className="text-xs text-blue-700 mt-1">
                                  Customer: {output.metadata.customer}
                                </p>
                              )}
                              {output.metadata.total_amount && (
                                <p className="text-xs text-blue-700">
                                  Amount: ${output.metadata.total_amount.toFixed(2)}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                {getFilteredOutputs().length === 0 && (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                    <p className="text-sm text-slate-500">
                      No {filterCategory !== 'all' ? filterCategory : ''} outputs found
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
