'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import DemoLayout from '@/elements/DemoLayout';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export default function Home() {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="min-h-screen">
        <DemoLayout />
      </main>
    </QueryClientProvider>
  );
}
