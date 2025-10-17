# TRIA AI-BPO Platform - Frontend

Professional POV demonstration frontend for the TRIA AI-BPO multi-agent system. Built with React 19, Next.js 15, and Tailwind CSS.

## Features

### 3-Column Layout
1. **Left Column**: Order Input Panel
   - WhatsApp message simulation
   - Outlet selection from database
   - Sample message templates
   - Real-time form validation

2. **Middle Column**: Agent Activity Visualization
   - Real-time status for 5 AI agents
   - Progress indicators
   - Task completion tracking
   - Color-coded agent states

3. **Right Column**: Generated Outputs
   - Order summary
   - Delivery Order (DO) preview
   - Invoice preview
   - Integration status

### 5 AI Agents
- **Customer Service Agent** (🎧) - Parses WhatsApp orders with GPT-4
- **Operations Orchestrator** (🎯) - Coordinates workflow across agents
- **Inventory Manager** (📦) - Verifies stock and generates DOs from Excel
- **Delivery Coordinator** (🚚) - Schedules deliveries and assigns drivers
- **Finance Controller** (💰) - Generates invoices and posts to Xero

### Real-Time Features
- Animated agent status updates
- Progress bars for each agent
- Task completion indicators
- Smooth transitions and animations

## Technology Stack

- **React 19**: Latest React with new hooks (useOptimistic, useTransition)
- **Next.js 15**: App Router with React Server Components
- **TypeScript**: Full type safety
- **Tailwind CSS**: Utility-first styling
- **TanStack Query**: Server state management
- **Lucide React**: Modern icon library

## Quick Start

### Prerequisites
- Node.js 18+ (20+ recommended)
- npm, yarn, or pnpm
- Backend API running at http://localhost:8001 (enhanced_api.py)

### Installation

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment**:
```bash
# Copy example environment file
cp .env.local.example .env.local

# Edit .env.local if needed (default: http://localhost:8001)
```

3. **Start development server**:
```bash
npm run dev
```

The frontend will be available at **http://localhost:3000**

### Build for Production

```bash
# Create optimized production build
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/                      # Next.js 15 App Router
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page (QueryClientProvider)
│   └── globals.css          # Global styles
├── elements/                 # React components (business logic)
│   ├── DemoLayout.tsx       # Main 3-column layout
│   ├── OrderInputPanel.tsx  # Left column - order input
│   ├── AgentActivityPanel.tsx # Middle column - agent visualization
│   ├── AgentCard.tsx        # Individual agent component
│   ├── OutputsPanel.tsx     # Right column - generated outputs
│   ├── OutletSelector.tsx   # Outlet dropdown with API integration
│   ├── api-client.ts        # FastAPI backend client
│   └── types.ts             # TypeScript interfaces
├── public/                   # Static assets
├── package.json             # Dependencies
├── tsconfig.json            # TypeScript config
├── tailwind.config.js       # Tailwind config
└── next.config.js           # Next.js config
```

## Architecture

### Index.tsx Pattern
- `app/page.tsx`: Only high-level orchestration + QueryClientProvider
- `elements/`: All business logic and UI components

### API Integration
- One API call per component (TanStack Query)
- Automatic loading states with skeleton components
- Error handling with fallback UI
- Real-time data from PostgreSQL

### State Management
- **Server State**: TanStack Query (API data, outlets, orders)
- **Local UI State**: useState (form inputs, processing status)
- **No Global State**: Prop drilling avoided by component composition

## Backend Integration

### Required Endpoints
The frontend expects these FastAPI endpoints:

```typescript
POST /api/process_order
{
  "whatsapp_message": string,
  "outlet_name"?: string
}
→ Returns: { success, order_id, run_id, message, details }

GET /api/outlets
→ Returns: { outlets: Outlet[], count: number }

GET /api/orders?limit=10
→ Returns: { orders: Order[], count: number }

GET /health
→ Returns: { status, database, runtime }
```

### CORS Configuration
Backend must allow frontend origin:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Demo Mode

The frontend includes a **simulation mode** that works without the backend:

- Simulates realistic agent workflow with timing delays
- Shows all 5 agents processing in sequence
- Generates sample outputs (DO, Invoice)
- Perfect for offline demos or testing

To enable full backend integration:
1. Start the FastAPI server (`python src/enhanced_api.py`)
2. Ensure PostgreSQL is running with outlets data
3. Verify CORS is configured correctly

## Customization

### Agent Colors
Edit `tailwind.config.js`:
```js
colors: {
  agent: {
    'customer-service': '#10b981',
    'orchestrator': '#8b5cf6',
    'inventory': '#f59e0b',
    'delivery': '#3b82f6',
    'finance': '#ec4899',
  }
}
```

### Sample Messages
Edit `OrderInputPanel.tsx`:
```typescript
const sampleMessages = [
  {
    label: 'Standard Order',
    text: 'Your custom message...',
  },
  // Add more samples
];
```

### Agent Workflow Timing
Edit `DemoLayout.tsx` `simulateAgentWorkflow()`:
```typescript
await delay(1500);  // Adjust timing in milliseconds
```

## Development Notes

### React 19 Features Used
- `use` API for suspense integration
- Automatic memoization via React Compiler
- `useTransition` for smooth UI updates

### Next.js 15 Features
- App Router architecture
- React Server Components (RSC)
- Turbopack for faster builds

### Performance
- Lazy loading for heavy components
- Optimized re-renders with React Compiler
- Responsive design (mobile-first)

## Troubleshooting

### Backend Connection Issues
```
Error: Failed to fetch outlets
```
**Solution**: Check backend is running at http://localhost:8001 (enhanced_api.py) and CORS is configured.

### Build Errors
```
Module not found: Can't resolve '@/elements/...'
```
**Solution**: Ensure `tsconfig.json` has correct paths configuration.

### Port Already in Use
```
Port 3000 is already in use
```
**Solution**: Stop other Next.js instances or change port:
```bash
npm run dev -- -p 3001
```

## Production Deployment

### Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables
Set in production:
```
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

## License

Part of the TRIA AI-BPO Platform - see main project LICENSE.

## Support

For issues or questions:
1. Check backend API is running
2. Verify database has outlet data
3. Check browser console for errors
4. Review backend logs for CORS issues
