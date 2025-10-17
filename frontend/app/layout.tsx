import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TRIA AI-BPO Platform',
  description: 'Multi-Agent AI-BPO System for Supply Chain Automation',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
