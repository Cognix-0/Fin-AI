'use client';
import { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Plus } from 'lucide-react';

import { expensesApi } from '@/lib/api/finance';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useAddExpense, useToast } from '@/hooks/useFinance';
import { ExpenseStatus } from '@/types/finance';
import { ExpensesTable } from '@/components/dashboard/ExpensesTable';
import { NewExpenseModal } from '@/components/dashboard/NewExpenseModal';
import { ExpenseDetailModal } from './ExpenseDetailModal';

type Tab = ExpenseStatus | 'all';

const TABS: { value: Tab; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'draft', label: 'Drafts' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

export function ExpensesView() {
  const { user } = useCurrentUser();
  const [tab, setTab] = useState<Tab>('all');
  const [selected, setSelected] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const { flash, toastNode } = useToast();
  const addExpense = useAddExpense(flash);

  // One tiny request per tab just to read `total` for the badge
  const counts = useQueries({
    queries: TABS.map((t) => ({
      queryKey: ['expenses', 'count', t.value],
      queryFn: () => expensesApi.list({ status: t.value === 'all' ? undefined : t.value, page_size: 1 }),
      enabled: !!user,
    })),
  });

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1>Expenses</h1>
          <p className="muted">
            Everything you can see, with filters and CSV export. Click a row for details, history and actions.
          </p>
        </div>
        <div className="page-head-actions">
          <button className="btn btn--primary btn--sm" onClick={() => setModalOpen(true)}>
            <Plus size={16} aria-hidden="true" />
            New expense
          </button>
        </div>
      </div>

      {toastNode}

      <div className="tabs" role="tablist" aria-label="Expense status">
        {TABS.map((t, i) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            className={`tab ${tab === t.value ? 'is-active' : ''}`}
            onClick={() => setTab(t.value)}
          >
            {t.label}
            <span className="tab-count">{counts[i].data?.total ?? '·'}</span>
          </button>
        ))}
      </div>

      <section className="card">
        {user && (
          <ExpensesTable
            advanced
            pageSize={15}
            status={tab}
            onSelect={(e) => setSelected(e.id)}
            onError={(m) => flash(m, 'error')}
          />
        )}
      </section>

      <ExpenseDetailModal expenseId={selected} onClose={() => setSelected(null)} onChanged={flash} />
      <NewExpenseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={addExpense}
        defaultDepartment={user?.department}
      />
    </div>
  );
}
