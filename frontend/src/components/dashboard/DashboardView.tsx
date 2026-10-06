'use client';
import { useMemo, useState } from 'react';
import { Info, Plus, Sparkles, TriangleAlert } from 'lucide-react';

import {
  Expense, Period, PERIODS, aiInsights, budgets, initialExpenses, monthlySpend,
} from '@/lib/mock/dashboard';
import { ExpenseFormValues } from '@/lib/validation/expense';
import { formatMoney, formatMoneyCompact } from '@/lib/format';
import { canApprove, formatRole, useCurrentUser } from '@/hooks/useCurrentUser';
import { Alert } from '@/components/ui/Alert';

import { Kpi, KpiCards } from './KpiCards';
import { SpendingChart } from './SpendingChart';
import { CategoryBreakdown } from './CategoryBreakdown';
import { BudgetList } from './BudgetList';
import { PendingApprovals } from './PendingApprovals';
import { ExpensesTable } from './ExpensesTable';
import { NewExpenseModal } from './NewExpenseModal';

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}

export function DashboardView() {
  const { user, loading } = useCurrentUser();
  const [period, setPeriod] = useState<Period>('30d');
  const [expenses, setExpenses] = useState<Expense[]>(initialExpenses);
  const [modalOpen, setModalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const approver = canApprove(user);
  const pending = useMemo(() => expenses.filter((e) => e.status === 'pending'), [expenses]);

  const kpis = useMemo<Kpi[]>(() => {
    const months = PERIODS.find((p) => p.value === period)!.months;
    const current = monthlySpend.slice(-months).reduce((s, m) => s + m.amount, 0);
    const previousSlice = monthlySpend.slice(-months * 2, -months);
    // 12-month view has no earlier data to compare against
    const previous = previousSlice.length === months
      ? previousSlice.reduce((s, m) => s + m.amount, 0)
      : undefined;
    const pendingTotal = pending.reduce((s, e) => s + e.amount, 0);
    const spent = budgets.reduce((s, b) => s + b.spent, 0);
    const limit = budgets.reduce((s, b) => s + b.limit, 0);
    const missingReceipts = expenses.filter((e) => !e.hasReceipt && e.status !== 'rejected').length;

    return [
      {
        label: 'Total spend',
        value: formatMoneyCompact(current),
        delta: previous ? ((current - previous) / previous) * 100 : undefined,
        detail: previous ? 'vs previous period' : 'across all departments',
      },
      {
        label: 'Pending approvals',
        value: String(pending.length),
        detail: `${formatMoney(pendingTotal)} awaiting review`,
      },
      {
        label: 'Budget used',
        value: `${Math.round((spent / limit) * 100)}%`,
        detail: `${formatMoneyCompact(spent)} of ${formatMoneyCompact(limit)} this month`,
      },
      {
        label: 'Missing receipts',
        value: String(missingReceipts),
        detail: missingReceipts === 1 ? 'expense needs a receipt' : 'expenses need a receipt',
      },
    ];
  }, [period, expenses, pending]);

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 3500);
  }

  function decide(id: string, status: 'approved' | 'rejected') {
    setExpenses((list) => list.map((e) => (e.id === id ? { ...e, status } : e)));
    flash(`${id} ${status}.`);
  }

  function addExpense(values: ExpenseFormValues, receipt: File | null, asDraft: boolean) {
    const nextId = Math.max(...expenses.map((e) => Number(e.id.split('-')[1]))) + 1;
    const expense: Expense = {
      id: `EXP-${nextId}`,
      date: values.date,
      merchant: values.merchant,
      category: values.category as Expense['category'],
      department: values.department,
      submittedBy: user?.full_name ?? 'You',
      amount: values.amount,
      status: asDraft ? 'draft' : 'pending',
      hasReceipt: receipt !== null,
    };
    setExpenses((list) => [expense, ...list]);
    flash(asDraft ? `${expense.id} saved as draft.` : `${expense.id} submitted for approval.`);
  }

  const firstName = user?.full_name.split(' ')[0];

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1>{loading ? 'Dashboard' : `${greeting()}${firstName ? `, ${firstName}` : ''}`}</h1>
          <p className="muted">
            {user
              ? `Signed in as ${user.roles.map(formatRole).join(', ') || 'Member'} · here’s where company spend stands.`
              : 'Here’s where company spend stands.'}
          </p>
        </div>
        <div className="page-head-actions">
          <div className="segmented" role="group" aria-label="Reporting period">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                className={period === p.value ? 'is-active' : ''}
                aria-pressed={period === p.value}
                onClick={() => setPeriod(p.value)}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button className="btn btn--primary btn--sm" onClick={() => setModalOpen(true)}>
            <Plus size={16} aria-hidden="true" />
            New expense
          </button>
        </div>
      </div>

      <p className="sample-note">
        <Info size={14} aria-hidden="true" />
        Finance figures are sample data until the expense API is built. Changes you make here are not saved.
      </p>

      {toast && (
        <div className="toast" role="status">
          <Alert type="success">{toast}</Alert>
        </div>
      )}

      <KpiCards items={kpis} />

      <div className="grid-2-1">
        <section className="card">
          <div className="card-head">
            <h2>Monthly spending</h2>
            <span className="muted">Selected period highlighted</span>
          </div>
          <SpendingChart
            data={monthlySpend}
            highlightLast={PERIODS.find((p) => p.value === period)!.months}
          />
        </section>

        <section className="card">
          <div className="card-head">
            <h2>{approver ? 'Needs your approval' : 'Awaiting approval'}</h2>
            <span className="count">{pending.length}</span>
          </div>
          <PendingApprovals expenses={pending} canApprove={approver} onDecision={decide} />
          {!approver && !loading && (
            <p className="approval-note muted">
              Managers and finance admins can approve or reject from here.
            </p>
          )}
        </section>
      </div>

      <div className="grid-3">
        <section className="card">
          <div className="card-head"><h2>Budget utilization</h2></div>
          <BudgetList budgets={budgets} />
        </section>

        <section className="card">
          <div className="card-head"><h2>Spend by category</h2></div>
          <CategoryBreakdown expenses={expenses} />
        </section>

        <section className="card">
          <div className="card-head">
            <h2><Sparkles size={16} aria-hidden="true" /> AI insights</h2>
          </div>
          <ul className="insight-list">
            {aiInsights.map((ins) => (
              <li key={ins.text} className={`insight insight--${ins.tone}`}>
                {ins.tone === 'warning'
                  ? <TriangleAlert size={16} aria-label="Warning" />
                  : <Info size={16} aria-label="Info" />}
                <span>{ins.text}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <h2>Recent expenses</h2>
        </div>
        <ExpensesTable expenses={expenses} />
      </section>

      <NewExpenseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={addExpense}
      />
    </div>
  );
}
