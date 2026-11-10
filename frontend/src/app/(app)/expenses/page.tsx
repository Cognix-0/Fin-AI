import type { Metadata } from 'next';
import { ExpensesView } from '@/components/expenses/ExpensesView';

export const metadata: Metadata = {
  title: 'Expenses — FinanceOS',
};

// Protected by proxy.ts
export default function Page() {
  return <ExpensesView />;
}
