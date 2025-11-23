/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./elements/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Safelist dynamic color classes used in OutputsPanel.enhanced
  safelist: [
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
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        agent: {
          'customer-service': '#10b981',
          'orchestrator': '#8b5cf6',
          'inventory': '#f59e0b',
          'delivery': '#3b82f6',
          'finance': '#ec4899',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      }
    },
  },
  plugins: [],
}
