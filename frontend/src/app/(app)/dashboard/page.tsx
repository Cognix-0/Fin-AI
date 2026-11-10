import type { Metadata } from 'next';
import { DashboardView } from '@/components/dashboard/DashboardView';

export const metadata: Metadata = {
  title: 'Dashboard — FinanceOS',
};

// This page is protected by proxy.ts
export default function DashboardPage() {
  return <DashboardView />;
}
