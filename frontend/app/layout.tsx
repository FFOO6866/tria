import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Tria AIBPO Platform',
  description: 'Multi-Agent AIBPO System for Supply Chain Automation',
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
