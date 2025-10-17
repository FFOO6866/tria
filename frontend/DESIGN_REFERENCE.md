# TRIA AI-BPO Frontend - Design Reference

## Visual Design Specifications

### Color Palette

#### Primary Colors
```css
Primary Blue:   #0ea5e9 (primary-500)
Primary Dark:   #0284c7 (primary-600)
Primary Light:  #7dd3fc (primary-300)
```

#### Agent Colors
```css
Customer Service: #10b981 (green-600)   🎧
Orchestrator:     #8b5cf6 (purple-600)  🎯
Inventory:        #f59e0b (amber-600)   📦
Delivery:         #3b82f6 (blue-600)    🚚
Finance:          #ec4899 (pink-600)    💰
```

#### Status Colors
```css
Success:  #10b981 (green-600)
Warning:  #f59e0b (amber-600)
Error:    #ef4444 (red-600)
Info:     #3b82f6 (blue-600)
Idle:     #94a3b8 (slate-400)
```

### Typography

#### Font Family
```css
System Font Stack:
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
"Helvetica Neue", Arial, sans-serif
```

#### Font Sizes
```css
Header:       24px (text-2xl)
Subheader:    18px (text-lg)
Body:         14px (text-sm)
Small:        12px (text-xs)
Monospace:    14px (font-mono)
```

### Layout Grid

```
Desktop (1920px)
┌────────────────────────────────────────────────────────────────┐
│  Header (60px height)                                          │
├──────────────┬──────────────────┬──────────────────────────────┤
│              │                  │                              │
│  Left Panel  │  Middle Panel    │  Right Panel                 │
│  (33%)       │  (33%)           │  (33%)                       │
│              │                  │                              │
│  Max 640px   │  Max 640px       │  Max 640px                   │
│              │                  │                              │
└──────────────┴──────────────────┴──────────────────────────────┘

Tablet (768px)
┌────────────────────────────────────┐
│  Header                            │
├────────────────────────────────────┤
│  Left Panel (100%)                 │
├────────────────────────────────────┤
│  Middle Panel (100%)               │
├────────────────────────────────────┤
│  Right Panel (100%)                │
└────────────────────────────────────┘

Mobile (375px)
┌──────────────────┐
│  Header          │
├──────────────────┤
│  Tabs:           │
│  [Input|Activity|│
│   Output]        │
├──────────────────┤
│  Active Panel    │
│  (100%)          │
│                  │
└──────────────────┘
```

### Component Specifications

#### Header
```
Height: 60px
Background: White (#ffffff)
Border Bottom: 1px solid #e2e8f0 (slate-200)
Padding: 16px 24px
Shadow: sm (subtle drop shadow)

Elements:
- Logo (40x40px rounded square, gradient blue)
- Title "TRIA AI-BPO Platform" (24px, bold)
- Subtitle "Multi-Agent Supply Chain Automation" (12px, slate-500)
- Status indicator (right-aligned)
```

#### Card Component
```
Background: White (#ffffff)
Border: 1px solid #e2e8f0 (slate-200)
Border Radius: 8px
Shadow: md (0 4px 6px rgba(0,0,0,0.1))
Padding: 24px

Header Section:
- Icon + Title (18px, bold)
- Subtitle (12px, slate-500)
- Border bottom: 1px solid #e2e8f0
- Padding: 16px 24px
```

#### Agent Card
```
Background: White (#ffffff)
Border: 2px solid (varies by state)
Border Radius: 8px
Padding: 16px
Transition: all 300ms ease

States:
- Idle:       border-slate-200
- Processing: border-{agent-color} + shadow-lg + animate-pulse
- Completed:  border-green-400 + bg-green-50
- Error:      border-red-400 + bg-red-50

Elements:
- Agent icon (40x40px rounded, emoji)
- Agent name (14px, bold)
- Status text (12px, capitalize)
- Progress bar (height: 8px, rounded-full)
- Task list (12px, with bullet points)
```

#### Progress Bar
```
Container:
- Width: 100%
- Height: 8px
- Background: #e2e8f0 (slate-200)
- Border radius: 9999px (fully rounded)

Fill:
- Background: current color (agent-color)
- Transition: width 500ms ease
- Border radius: 9999px
```

#### Button Styles

**Primary Button:**
```css
Background: #0284c7 (primary-600)
Hover: #0369a1 (primary-700)
Color: White
Padding: 12px 24px
Border Radius: 8px
Font Weight: 600
Transition: all 200ms

Disabled:
  Opacity: 0.5
  Cursor: not-allowed
```

**Secondary Button:**
```css
Background: #e2e8f0 (slate-200)
Hover: #cbd5e1 (slate-300)
Color: #1e293b (slate-800)
Padding: 8px 16px
Border Radius: 8px
Font Weight: 600
```

#### Form Elements

**Text Input / Textarea:**
```css
Border: 1px solid #cbd5e1 (slate-300)
Border Radius: 8px
Padding: 12px 16px
Font Size: 14px

Focus:
  Border Color: #0ea5e9 (primary-500)
  Ring: 2px solid #0ea5e9
  Outline: none
```

**Select Dropdown:**
```css
Same as text input
Plus dropdown arrow (chevron-down icon)
```

### Animation Specifications

#### Agent Status Change
```css
Duration: 300ms
Timing: ease-in-out
Properties: border-color, background-color, box-shadow
```

#### Task List Item (Slide In)
```css
Animation: fade-in + slide-in-from-left
Duration: 300ms
Delay: stagger by 100ms per item
```

#### Progress Bar Fill
```css
Duration: 500ms
Timing: ease-out
Property: width
```

#### Spinner / Loader
```css
Animation: spin
Duration: 1s (3s for slow version)
Timing: linear
Iteration: infinite
```

#### Pulse Effect (Active Agents)
```css
Animation: pulse
Duration: 2s
Timing: cubic-bezier(0.4, 0, 0.6, 1)
Iteration: infinite
```

### Spacing System

```
xs:  4px   (gap-1)
sm:  8px   (gap-2)
md:  16px  (gap-4)
lg:  24px  (gap-6)
xl:  32px  (gap-8)
2xl: 48px  (gap-12)
```

### Icon Specifications

#### Icon Library
- **lucide-react** (consistent, modern icons)
- Size: 20px (w-5 h-5) for most icons
- Size: 16px (w-4 h-4) for small icons
- Stroke width: 2px

#### Common Icons
```
MessageSquare  → WhatsApp input
Users          → Agent activity
FileText       → Generated outputs
Send           → Submit button
Loader2        → Loading spinner
CheckCircle2   → Success indicator
AlertCircle    → Error indicator
Bot            → Idle agent
Package        → Order/inventory
Truck          → Delivery
DollarSign     → Finance/invoice
Download       → Download action
```

### Responsive Breakpoints

```css
Mobile:  < 768px   (1 column, stacked)
Tablet:  768-1024px (2 columns)
Desktop: > 1024px   (3 columns)
Wide:    > 1536px   (3 columns, max-width constrained)
```

### Dark Mode Support (Future)

```css
Background: #0f172a (slate-900)
Surface: #1e293b (slate-800)
Border: #334155 (slate-700)
Text: #f1f5f9 (slate-100)
Muted: #64748b (slate-500)

Agent colors remain same (good contrast on dark)
```

### Accessibility

#### Contrast Ratios
- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum
- UI components: 3:1 minimum

#### Focus States
- Visible focus ring (2px solid primary-500)
- Skip to content link
- Keyboard navigation support

#### Screen Reader Support
- Semantic HTML (header, main, section, article)
- ARIA labels for icons
- Alt text for images
- Status announcements for agent updates

### Micro-Interactions

#### Hover Effects
```
Buttons: Scale 1.02 + shadow increase
Cards: Shadow increase
Links: Underline + color change
```

#### Click Effects
```
Buttons: Scale 0.98 (press down)
Cards: Border pulse
Checkboxes: Bounce animation
```

#### Loading States
```
Skeleton screens with shimmer animation
Spinner for active operations
Progress bars for multi-step processes
```

### Error States

```
Inline Errors:
  Red border + red text below input
  Icon: AlertCircle

Toast Notifications:
  Position: Top-right
  Duration: 5s
  Colors: green (success), red (error), blue (info)
  Animation: slide-in from right
```

### Success States

```
Success Banner:
  Background: green-50
  Border: 2px solid green-200
  Icon: CheckCircle2 (green-600)
  Animation: fade-in + slide-in-from-bottom

Status Indicators:
  Green checkmark + text
  Smooth transition from processing → completed
```

### Loading States

```
Skeleton Screens:
  Background: slate-200
  Shimmer: Animated gradient (slate-200 → slate-300)
  Height matches actual content
  Border radius matches components

Spinners:
  Border: 2px solid
  Border-top: transparent
  Size: 20px (inline), 32px (page-level)
```

## Design Principles

### 1. Clarity Over Complexity
- Clean, uncluttered interface
- Clear visual hierarchy
- Obvious call-to-actions

### 2. Real-Time Feedback
- Immediate response to user actions
- Visible progress indicators
- Status updates without page refresh

### 3. Professional Aesthetics
- Consistent spacing and alignment
- Subtle shadows and borders
- Smooth animations (not distracting)

### 4. Trustworthy Design
- Enterprise-grade appearance
- Reliable status indicators
- Complete audit trail visibility

### 5. Responsive by Default
- Mobile-first approach
- Touch-friendly controls (min 44x44px)
- Readable on all screen sizes

## Component Examples

### Order Input Panel
```
┌─────────────────────────────────┐
│ 🎧 WhatsApp Order Input         │ ← Header with icon
│ Simulate incoming customer order│ ← Subtitle
├─────────────────────────────────┤
│                                 │
│ Customer Outlet ▼               │ ← Dropdown (select)
│ [Pacific Pizza - Downtown]      │
│                                 │
│ WhatsApp Message                │ ← Label
│ ┌─────────────────────────────┐ │
│ │ Type or paste message...    │ │ ← Textarea
│ │                             │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ Quick Samples:                  │
│ [Standard] [Urgent] [Large]     │ ← Sample buttons
│                                 │
│ ┌───────────────────────────┐   │
│ │  📤 Process Order         │   │ ← Primary button
│ └───────────────────────────┘   │
│                                 │
│ ℹ️ Demo Mode: This simulates... │ ← Info box
└─────────────────────────────────┘
```

### Agent Card (Active)
```
┌─────────────────────────────────┐
│ 🎯 Operations Orchestrator      │ ← Icon + name
│ processing              ⟳       │ ← Status + spinner
├─────────────────────────────────┤
│ ████████░░░░░░░░░░░░░░░░  50%   │ ← Progress bar
├─────────────────────────────────┤
│ • Received order ✓              │ ← Task (completed)
│ • Analyzing requirements ✓      │ ← Task (completed)
│ • Coordinating agents... ⟳      │ ← Task (active)
└─────────────────────────────────┘
```

### Output Panel (Success)
```
┌─────────────────────────────────┐
│ 📄 Generated Outputs            │
│ Delivery Order & Invoice        │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ ✅ Order Processed!         │ │ ← Success banner
│ │ All agents completed        │ │
│ └─────────────────────────────┘ │
│                                 │
│ 📦 Order Summary                │
│ Customer: Pacific Pizza         │
│ Total: 1200 boxes              │
│ Amount: $3,450.00              │
│                                 │
│ 🚚 Delivery Order               │ ← DO preview card
│ DO-2024-001                     │
│ [Download] →                    │
│                                 │
│ 💰 Invoice                      │ ← Invoice preview card
│ INV-2024-001                    │
│ [Download] →                    │
│                                 │
│ Integration Status:             │
│ ✓ Database ✓ Excel              │
│ ✓ Xero ✓ GPT-4                  │
└─────────────────────────────────┘
```

---

## Implementation Notes

### CSS Framework
- **Tailwind CSS 3.4+** for utility classes
- Custom theme extensions in `tailwind.config.js`
- Global styles in `app/globals.css`

### Component Library
- **No UI library dependencies** (custom components)
- Lucide React for icons
- Native HTML form elements

### State Management
- React useState for local state
- TanStack Query for server state
- No Redux/Zustand needed (simple app)

### Performance
- Lazy load heavy components
- Optimize re-renders with React Compiler
- Use CSS transforms for animations (GPU-accelerated)

---

This design reference ensures consistency across all components and provides clear specifications for any future development or modifications.
