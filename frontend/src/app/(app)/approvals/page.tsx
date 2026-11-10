import type { Metadata } from 'next';
import { ApprovalsView } from '@/components/approvals/ApprovalsView';

export const metadata: Metadata = {
  title: 'Approvals — FinanceOS',
};

// Protected by proxy.ts
export default function Page() {
  return <ApprovalsView />;
}
