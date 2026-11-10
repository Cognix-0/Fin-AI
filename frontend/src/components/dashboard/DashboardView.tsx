'use client';
import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Info, Plus, Sparkles, TriangleAlert } from 'lucide-react';

import { PERIODS } from '@/lib/constants/finance';
import { analyticsApi, budgetsApi, expensesApi } from '@/lib/api/finance';
import { formatMoney, formatMoneyCompact } from '@/lib/format';
import { canApprove, formatRole, useCurrentUser } from '@/hooks/useCurrentUser';
import { useAddExpense, useRefreshFinance, useToast } from '@/hooks/useFinance';
import { AnalyticsSummary, Expense, Period } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';

import { Kpi, KpiCards } from './KpiCards';
import { SpendingChart } from './SpendingChart';
import { CategoryBreakdown } from './CategoryBreakdown';
import { BudgetList } from './BudgetList';
import { PendingApprovals } from './PendingApprovals';
import { ExpensesTable } from './ExpensesTable';
import { NewExpenseModal } from './NewExpenseModal';
import { ExpenseDetailModal } from '@/components/expenses/ExpenseDetailModal';

const SCOPE_TEXT: Record<AnalyticsSummary['scope'], string> = {
  company: 'here’s where company spend stands.',
  department: 'here’s where your department’s spend stands.',
  personal: 'here’s a summary of your expenses.',
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}

function buildKpis(s: AnalyticsSummary | undefined, loading: boolean): Kpi[] {
  const dash = loading ? '…' : '—';
  if (!s) {
    return ['Total spend', 'Pending approvals', 'Budget used', 'Missing receipts'].map((label) => ({
      label, value: dash, detail: '',
    }));
  }
  const k = s.kpis;
  return [
    {
      label: 'Total spend',
      value: formatMoneyCompact(k.total_spend),
      delta: k.change_pct ?? undefined,
      detail: k.change_pct !== null
        ? 'vs previous period'
        : `${k.expense_count} expense${k.expense_count === 1 ? '' : 's'}`,
    },
    {
      label: 'Pending approvals',
      value: String(k.pending_count),
      detail: `${formatMoney(k.pending_total)} awaiting review`,
    },
    {
      label: 'Budget used',
      value: k.budget_utilization === null ? '—' : `${Math.round(k.budget_utilization)}%`,
      detail: k.budget_limit
        ? `${formatMoneyCompact(k.budget_committed)} of ${formatMoneyCompact(k.budget_limit)} this month`
        : 'No budgets set this month',
    },
    {
      label: 'Missing receipts',
      value: String(k.missing_receipts),
      detail: k.missing_receipts === 1 ? 'expense needs a receipt' : 'expenses need a receipt',
    },
  ];
}

export function DashboardView() {
  const { user, loading } = useCurrentUser();
  const [period, setPeriod] = useState<Period>('30d');
  const [modalOpen, setModalOpen] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const { flash, toastNode } = useToast();
  const refreshAll = useRefreshFinance();
  const addExpense = useAddExpense(flash);

  const approver = canApprove(user);

  const summary = useQuery({
    queryKey: ['analytics', 'summary', period],
    queryFn: () => analyticsApi.summary(period),
    enabled: !!user,
  });
  const budgets = useQuery({
    queryKey: ['budgets', 'current'],
    queryFn: () => budgetsApi.list(),
    enabled: !!user,
  });
  const pending = useQuery({
    queryKey: ['expenses', 'pending'],
    queryFn: () => expensesApi.list({ status: 'pending', sort: '-created', page_size: 10 }),
    enabled: !!user,
  });

  const kpis = useMemo(() => buildKpis(summary.data, summary.isPending), [summary.data, summary.isPending]);

  const decide = useMutation({
    mutationFn: ({ e, reason }: { e: Expense; reason?: string }) =>
      reason === undefined ? expensesApi.approve(e.id) : expensesApi.reject(e.id, reason),
    onSuccess: (updated) => {
      flash(`${updated.reference} ${updated.status}.`);
      return refreshAll();
    },
    onError: (err: Error) => flash(err.message, 'error'),
  });

  const firstName = user?.full_name.split(' ')[0];
  const months = PERIODS.find((p) => p.value === period)!.months;
  const pendingItems = pending.data?.items ?? [];
  const loadError = summary.error ?? budgets.error ?? pending.error;

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1>{loading ? 'Dashboard' : `${greeting()}${firstName ? `, ${firstName}` : ''}`}</h1>
          <p className="muted">
            {user
              ? `Signed in as ${user.roles.map(formatRole).join(', ') || 'Member'}${user.department ? ` · ${user.department}` : ''} · ${SCOPE_TEXT[summary.data?.scope ?? 'company']}`
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

      {loadError && (
        <Alert type="error">Some figures couldn’t be loaded: {(loadError as Error).message}</Alert>
      )}

      {toastNode}

      <KpiCards items={kpis} />

      <div className="grid-2-1">
        <section className="card">
          <div className="card-head">
            <h2>Monthly spending</h2>
            <span className="muted">Approved + pending · selected period highlighted</span>
          </div>
          {summary.data
            ? <SpendingChart data={summary.data.monthly} highlightLast={months} />
            : <p className="empty">{summary.isPending ? 'Loading…' : 'No data'}</p>}
        </section>

        <section className="card">
          <div className="card-head">
            <h2>{approver ? 'Needs your approval' : 'Awaiting approval'}</h2>
            <span className="count">{pending.data?.total ?? 0}</span>
          </div>
          {pending.isPending ? (
            <p className="empty">Loading…</p>
          ) : (
            <PendingApprovals
              expenses={pendingItems}
              busyId={decide.isPending ? decide.variables?.e.id ?? null : null}
              onApprove={(e) => decide.mutate({ e })}
              onReject={(e, reason) => decide.mutate({ e, reason })}
            />
          )}
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
          {budgets.data
            ? <BudgetList budgets={budgets.data} />
            : <p className="empty">{budgets.isPending ? 'Loading…' : 'No data'}</p>}
        </section>

        <section className="card">
          <div className="card-head"><h2>Spend by category</h2></div>
          <CategoryBreakdown rows={summary.data?.by_category ?? []} />
        </section>

        <section className="card">
          <div className="card-head">
            <h2><Sparkles size={16} aria-hidden="true" /> Insights</h2>
          </div>
          <ul className="insight-list">
            {(summary.data?.insights ?? []).map((ins) => (
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
          <h2>Expenses</h2>
        </div>
        {user && <ExpensesTable onError={(m) => flash(m, 'error')} onSelect={(e) => setSelected(e.id)} />}
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
