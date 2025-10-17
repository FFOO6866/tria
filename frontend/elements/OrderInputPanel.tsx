'use client';

import { useState } from 'react';
import { MessageSquare, Send } from 'lucide-react';

interface OrderInputPanelProps {
  onSubmit: (message: string, outlet: string) => void;
  isProcessing: boolean;
}

export default function OrderInputPanel({ onSubmit, isProcessing }: OrderInputPanelProps) {
  const [message, setMessage] = useState('');
  const [outlet, setOutlet] = useState('Pacific Pizza - Downtown');

  const sampleMessages = [
    {
      label: 'Standard Order',
      text: 'Hi! Need 600 x 10", 200 x 12", and 400 x 14" boxes for Pacific Pizza Downtown. Regular delivery is fine.',
    },
    {
      label: 'Urgent Order',
      text: 'URGENT: Need 800 x 10" and 300 x 12" boxes ASAP for Pacific Pizza Downtown! Running low on stock.',
    },
    {
      label: 'Large Order',
      text: 'Placing order for Pacific Pizza Downtown: 1000 x 10", 500 x 12", 600 x 14" boxes. Standard delivery.',
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing) {
      onSubmit(message, outlet);
    }
  };

  const useSample = (text: string) => {
    setMessage(text);
  };

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-green-600" />
          <h2 className="text-lg font-semibold text-slate-900">WhatsApp Order Input</h2>
        </div>
        <p className="text-sm text-slate-500 mt-1">Simulate incoming customer order</p>
      </div>

      <div className="card-body flex-1 flex flex-col">
        <form onSubmit={handleSubmit} className="flex-1 flex flex-col gap-4">
          {/* Outlet Selection */}
          <div>
            <label htmlFor="outlet" className="block text-sm font-medium text-slate-700 mb-2">
              Customer Outlet
            </label>
            <select
              id="outlet"
              value={outlet}
              onChange={(e) => setOutlet(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={isProcessing}
            >
              <option>Pacific Pizza - Downtown</option>
              <option>Pacific Pizza - Uptown</option>
              <option>Pacific Pizza - Westside</option>
              <option>Luigi's Italian Kitchen</option>
              <option>Mama Mia Pizzeria</option>
              <option>Golden Crust Pizza</option>
            </select>
          </div>

          {/* Message Input */}
          <div className="flex-1 flex flex-col">
            <label htmlFor="message" className="block text-sm font-medium text-slate-700 mb-2">
              WhatsApp Message
            </label>
            <textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type or paste a WhatsApp order message..."
              className="flex-1 px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none font-mono text-sm"
              disabled={isProcessing}
              rows={10}
            />
          </div>

          {/* Sample Messages */}
          <div>
            <p className="text-xs font-medium text-slate-600 mb-2">Quick Samples:</p>
            <div className="flex flex-wrap gap-2">
              {sampleMessages.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => useSample(sample.text)}
                  disabled={isProcessing}
                  className="btn-secondary text-xs py-1 px-3"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isProcessing || !message.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {isProcessing ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Processing Order...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Process Order
              </>
            )}
          </button>
        </form>

        {/* Info Box */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800">
            <strong>Demo Mode:</strong> This simulates the Customer Service Agent parsing WhatsApp
            messages. Watch the agents coordinate to process your order in real-time!
          </p>
        </div>
      </div>
    </div>
  );
}
