'use client';

import { useQuery } from '@tanstack/react-query';
import { listOutlets } from './api-client';
import { Loader2 } from 'lucide-react';

interface OutletSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export default function OutletSelector({ value, onChange, disabled }: OutletSelectorProps) {
  const { data: outlets, isPending, error } = useQuery({
    queryKey: ['outlets'],
    queryFn: listOutlets,
  });

  if (error) {
    return (
      <div>
        <label htmlFor="outlet" className="block text-sm font-medium text-slate-700 mb-2">
          Customer Outlet
        </label>
        <select
          id="outlet"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          disabled={disabled}
        >
          <option>Pacific Pizza - Downtown</option>
          <option>Pacific Pizza - Uptown</option>
          <option>Pacific Pizza - Westside</option>
        </select>
        <p className="text-xs text-amber-600 mt-1">Using fallback outlets (API unavailable)</p>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor="outlet" className="block text-sm font-medium text-slate-700 mb-2">
        Customer Outlet
        {isPending && <Loader2 className="w-3 h-3 inline-block ml-2 animate-spin" />}
      </label>
      <select
        id="outlet"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        disabled={disabled || isPending}
      >
        {isPending ? (
          <option>Loading outlets...</option>
        ) : outlets && outlets.length > 0 ? (
          outlets.map((outlet) => (
            <option key={outlet.id} value={outlet.name}>
              {outlet.name}
            </option>
          ))
        ) : (
          <>
            <option>Pacific Pizza - Downtown</option>
            <option>Pacific Pizza - Uptown</option>
            <option>Pacific Pizza - Westside</option>
          </>
        )}
      </select>
      {outlets && outlets.length > 0 && (
        <p className="text-xs text-green-600 mt-1">✓ Loaded {outlets.length} outlets from database</p>
      )}
    </div>
  );
}
