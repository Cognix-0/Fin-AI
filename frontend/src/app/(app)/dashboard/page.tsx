import type { Metadata } from 'next';
import { DashboardView } from '@/components/dashboard/DashboardView';

export const metadata: Metadata = {
  title: 'Dashboard — FinanceOS',
};

// This page is protected by middleware.ts
export default function DashboardPage() {
  return <DashboardView />;
}
