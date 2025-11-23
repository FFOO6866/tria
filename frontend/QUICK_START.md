# Quick Start - Enhanced Generated Outputs

## ⚡ 5-Minute Integration

### Step 1: Update Types (Copy-Paste)

Open `frontend/elements/types.ts` and add to the end:

```typescript
// ============================================================
// GENERATED OUTPUTS TYPES (Enhanced)
// ============================================================

export interface AgentOutputMetadata {
  do_number?: string;
  invoice_number?: string;
  customer?: string;
  customer_id?: string;
  total_amount?: number;
  total_quantity?: number;
  subtotal?: number;
  tax_amount?: number;
  inventory_summary?: Array<{
    sku: string;
    product_name: string;
    before: number;
    requested: number;
    after: number;
    status: string;
  }>;
  line_items?: Array<{
    item_code: string;
    description: string;
    quantity: number;
    unit_price: number;
  }>;
}

export interface AgentOutput {
  agent_name: string;
  category: 'inventory' | 'delivery' | 'finance' | 'orders' | 'general';
  status: 'idle' | 'processing' | 'completed' | 'error';
  current_task: string;
  details: string[];
  metadata?: AgentOutputMetadata;
  date: string;
  time: string;
  started_at: string;
  completed_at?: string;
}

export interface GeneratedOutputsSummary {
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
```

### Step 2: Update DemoLayout (1 Line Change)

Open `frontend/elements/DemoLayout.tsx` and change line 6:

```typescript
// OLD (line 6):
import OutputsPanel from './OutputsPanel';

// NEW (line 6):
import OutputsPanel from './OutputsPanel.enhanced';
```

### Step 3: Update Tailwind Config (Prevent Color Issues)

Open `frontend/tailwind.config.js` or `frontend/tailwind.config.ts` and add:

```javascript
module.exports = {
  // ... existing config ...
  safelist: [
    // Add these to ensure dynamic colors work
    'bg-green-50', 'bg-green-100', 'border-green-200', 'border-green-300',
    'text-green-600', 'text-green-700', 'text-green-800', 'text-green-900',
    'bg-blue-50', 'bg-blue-100', 'border-blue-200', 'border-blue-300',
    'text-blue-600', 'text-blue-700', 'text-blue-800', 'text-blue-900',
    'bg-pink-50', 'bg-pink-100', 'border-pink-200', 'border-pink-300',
    'text-pink-600', 'text-pink-700', 'text-pink-800', 'text-pink-900',
    'bg-purple-50', 'bg-purple-100', 'border-purple-200', 'border-purple-300',
    'text-purple-600', 'text-purple-700', 'text-purple-800', 'text-purple-900',
    'bg-slate-50', 'bg-slate-100', 'border-slate-200', 'border-slate-300',
    'text-slate-600', 'text-slate-700', 'text-slate-800', 'text-slate-900',
  ],
};
```

### Step 4: Test It

```bash
cd frontend
npm run dev
```

Visit: http://localhost:3000

1. Process an order
2. See Summary view (same as before)
3. Click "Detailed" tab
4. See full agent outputs with inventory, DO details, invoices

---

## ✅ Verification Checklist

- [ ] Summary view looks identical to original
- [ ] Can toggle between Summary/Detailed
- [ ] Detailed view shows agent cards
- [ ] Filter pills work (All, Inventory, Delivery, Finance, Orders)
- [ ] Can expand/collapse agent cards
- [ ] Inventory shows before/after quantities
- [ ] DO shows line items and totals
- [ ] Invoice shows subtotal, tax, total
- [ ] Colors match theme (green, blue, pink, purple)

---

## 🐛 Common Issues

### Issue: "Module not found: Can't resolve './OutputsPanel.enhanced'"

**Fix**: Make sure the file exists at:
```
frontend/elements/OutputsPanel.enhanced.tsx
```

### Issue: Colors not showing (all gray)

**Fix**: Add safelist to `tailwind.config.js` (see Step 3)

### Issue: API returns 404

**Fix**: Ensure backend is running:
```bash
# In project root
docker-compose up -d
# or
python src/enhanced_api.py
```

### Issue: Detailed view shows "No outputs"

**Fix**: Process an order first. The detailed view fetches data from the backend.

---

## 🚀 That's It!

You now have enhanced outputs showing:
- ✅ Draft DO with store, qty, delivery date, line items
- ✅ Invoice with detailed breakdown (subtotal, tax, total)
- ✅ Inventory before/after for each product
- ✅ Filtering by category and date
- ✅ Expandable detailed view

**Questions?** Check `GENERATED_OUTPUTS_INTEGRATION.md` for full documentation.
