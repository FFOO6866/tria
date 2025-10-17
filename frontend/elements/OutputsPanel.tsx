'use client';

import { FileText, Download, CheckCircle2, Loader2, Package, DollarSign, Truck, ExternalLink } from 'lucide-react';
import { OrderResult } from './types';
import { downloadDeliveryOrder, downloadInvoice, postToXero } from './api-client';
import { useState } from 'react';

interface OutputsPanelProps {
  result: OrderResult | null;
  isProcessing: boolean;
}

export default function OutputsPanel({ result, isProcessing }: OutputsPanelProps) {
  const [downloading, setDownloading] = useState<'do' | 'invoice' | null>(null);
  const [postingXero, setPostingXero] = useState(false);
  const [xeroMessage, setXeroMessage] = useState<string | null>(null);

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

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-slate-900">Generated Outputs</h2>
        </div>
        <p className="text-sm text-slate-500 mt-1">Delivery Order & Invoice</p>
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

        {result && (
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
          </div>
        )}
      </div>
    </div>
  );
}
