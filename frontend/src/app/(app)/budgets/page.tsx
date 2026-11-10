import type { Metadata } from 'next';
import { BudgetsView } from '@/components/budgets/BudgetsView';

export const metadata: Metadata = {
  title: 'Budgets — FinanceOS',
};

// Protected by proxy.ts
export default function Page() {
  return <BudgetsView />;
}
