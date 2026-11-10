'use client';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, CircleCheck, Copy, OctagonAlert, Save, Trash2, TriangleAlert } from 'lucide-react';

import { budgetsApi } from '@/lib/api/finance';
import { formatMoney, formatMoneyCompact } from '@/lib/format';
import { isFinance, useCurrentUser } from '@/hooks/useCurrentUser';
import { useRefreshFinance, useToast } from '@/hooks/useFinance';
import { Budget, BudgetStatus } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { KpiCards } from '@/components/dashboard/KpiCards';

const STATUS = {
  over_budget: { tone: 'critical', label: 'Over budget', Icon: OctagonAlert },
  near_limit: { tone: 'warning', label: 'Near limit', Icon: TriangleAlert },
  on_track: { tone: 'good', label: 'On track', Icon: CircleCheck },
  no_budget: { tone: 'muted', label: 'No budget', Icon: CircleCheck },
} satisfies Record<BudgetStatus, unknown>;

const monthLabel = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' });

/** 'YYYY-MM' shifted by n months */
function shiftMonth(ym: string, n: number) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 1 + n, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function without(obj: Record<string, string>, key: string) {
  const next = { ...obj };
  delete next[key];
  return next;
}

const thisMonth = () => {
  const d = new Date();   // local time, not UTC, so the month flips at local midnight
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
};

export function BudgetsView() {
  const { user } = useCurrentUser();
  const canManage = isFinance(user);
  const refresh = useRefreshFinance();
  const { flash, toastNode } = useToast();
  const [month, setMonth] = useState(thisMonth);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [copyOpen, setCopyOpen] = useState(false);
  const [overwrite, setOverwrite] = useState(false);

  const monthDate = `${month}-01`;
  const label = monthLabel.format(new Date(`${monthDate}T00:00:00`));
  const prevLabel = monthLabel.format(new Date(`${shiftMonth(month, -1)}-01T00:00:00`));

  const budgets = useQuery({
    queryKey: ['budgets', 'month', month],
    queryFn: () => budgetsApi.list(monthDate, true),
    enabled: !!user,
  });

  function goTo(m: string) {
    setMonth(m);
    setDrafts({});
    setCopyOpen(false);
  }

  const save = useMutation({
    mutationFn: ({ dept, limit }: { dept: string; limit: number }) => budgetsApi.upsert(dept, monthDate, limit),
    onSuccess: async (b) => {
      setDrafts((d) => without(d, b.department));
      flash(`${b.department} budget for ${label} set to ${formatMoney(b.limit)}.`);
      await refresh();
    },
    onError: (e: Error) => flash(e.message, 'error'),
  });

  const remove = useMutation({
    mutationFn: (b: Budget) => budgetsApi.remove(b.id!),
    onSuccess: async (_, b) => {
      flash(`${b.department} budget for ${label} removed.`);
      await refresh();
    },
    onError: (e: Error) => flash(e.message, 'error'),
  });

  const copy = useMutation({
    mutationFn: () => budgetsApi.copy(`${shiftMonth(month, -1)}-01`, monthDate, overwrite),
    onSuccess: async (r) => {
      flash(`Copied from ${prevLabel}: ${r.created} created, ${r.updated} updated, ${r.skipped} kept.`);
      setCopyOpen(false);
      setOverwrite(false);
      setDrafts({});
      await refresh();
    },
    onError: (e: Error) => flash(e.message, 'error'),
  });

  const items = budgets.data ?? [];
  const budgeted = items.filter((b) => b.id !== null);
  const totalLimit = budgeted.reduce((s, b) => s + b.limit, 0);
  const totalSpent = items.reduce((s, b) => s + b.spent, 0);
  const totalPending = items.reduce((s, b) => s + b.pending, 0);
  const over = items.filter((b) => b.status === 'over_budget').length;
  const near = items.filter((b) => b.status === 'near_limit').length;

  const kpis = budgets.isPending
    ? ['Total budget', 'Approved spend', 'Remaining', 'Departments at risk'].map((l) => ({ label: l, value: '…', detail: '' }))
    : [
        {
          label: 'Total budget',
          value: formatMoneyCompact(totalLimit),
          detail: `${budgeted.length} of ${items.length} departments budgeted`,
        },
        {
          label: 'Approved spend',
          value: formatMoneyCompact(totalSpent),
          detail: `${formatMoney(totalPending)} more pending`,
        },
        {
          label: 'Remaining',
          value: formatMoneyCompact(totalLimit - totalSpent - totalPending),
          detail: totalLimit
            ? `${Math.round(((totalSpent + totalPending) / totalLimit) * 100)}% committed`
            : 'No budgets set',
        },
        {
          label: 'Departments at risk',
          value: String(over + near),
          detail: `${over} over budget · ${near} near limit`,
        },
      ];

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1>Budgets</h1>
          <p className="muted">
            Monthly limits per department against approved and pending spend.
            {!canManage && ' Only finance admins can change budgets.'}
          </p>
        </div>
        <div className="page-head-actions">
          <div className="month-nav">
            <button className="icon-btn" onClick={() => goTo(shiftMonth(month, -1))} aria-label="Previous month">
              <ChevronLeft size={16} />
            </button>
            <label>
              <span className="sr-only">Month</span>
              <input type="month" value={month} onChange={(e) => e.target.value && goTo(e.target.value)} />
            </label>
            <button className="icon-btn" onClick={() => goTo(shiftMonth(month, 1))} aria-label="Next month">
              <ChevronRight size={16} />
            </button>
          </div>
          {month !== thisMonth() && (
            <button className="btn btn--ghost btn--sm" onClick={() => goTo(thisMonth())}>This month</button>
          )}
          {canManage && (
            <button className="btn btn--ghost btn--sm" onClick={() => setCopyOpen((o) => !o)} aria-expanded={copyOpen}>
              <Copy size={15} aria-hidden="true" /> Copy from {prevLabel.split(' ')[0]}
            </button>
          )}
        </div>
      </div>

      {toastNode}

      {copyOpen && (
        <div className="card confirm-card">
          <p>
            Copy every department&apos;s budget from <strong>{prevLabel}</strong> into <strong>{label}</strong>.
          </p>
          <label className="check-field">
            <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
            Overwrite budgets already set for {label}
          </label>
          <div className="action-group">
            <Button variant="ghost" className="btn--sm" onClick={() => setCopyOpen(false)}>Cancel</Button>
            <Button className="btn--sm" loading={copy.isPending} onClick={() => copy.mutate()}>Copy budgets</Button>
          </div>
        </div>
      )}

      {budgets.isError && <Alert type="error">{(budgets.error as Error).message}</Alert>}

      <KpiCards items={kpis} />

      <section className="card">
        <div className="card-head">
          <h2>{label}</h2>
          <span className="muted cell-sub">“Used” counts approved + pending spend</span>
        </div>
        <div className="table-wrap">
          <table className="data-table budget-table">
            <thead>
              <tr>
                <th>Department</th>
                <th className="num">Limit</th>
                <th className="num">Approved</th>
                <th className="num">Pending</th>
                <th className="num">Remaining</th>
                <th style={{ width: '22%' }}>Used</th>
                <th>Status</th>
                {canManage && <th className="num"><span className="sr-only">Actions</span></th>}
              </tr>
            </thead>
            <tbody>
              {budgets.isPending ? (
                <tr><td colSpan={8} className="empty">Loading…</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={8} className="empty">No departments found.</td></tr>
              ) : (
                items.map((b) => {
                  const { tone, label: statusLabel, Icon } = STATUS[b.status as BudgetStatus];
                  const draft = drafts[b.department];
                  const draftNum = draft === undefined ? NaN : Number(draft);
                  const dirty = draft !== undefined && draft !== '' && draftNum !== b.limit;
                  const valid = Number.isFinite(draftNum) && draftNum >= 0;
                  const busy = (save.isPending && save.variables?.dept === b.department)
                    || (remove.isPending && remove.variables?.department === b.department);
                  return (
                    <tr key={b.department}>
                      <td className="cell-main">{b.department}</td>
                      <td className="num">
                        {canManage ? (
                          <input
                            className="money-input"
                            type="number"
                            min={0}
                            step={100}
                            inputMode="decimal"
                            aria-label={`${b.department} budget limit`}
                            placeholder="Set limit"
                            value={draft ?? (b.id === null ? '' : String(b.limit))}
                            onChange={(e) => setDrafts((d) => ({ ...d, [b.department]: e.target.value }))}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && dirty && valid) save.mutate({ dept: b.department, limit: draftNum });
                              if (e.key === 'Escape') setDrafts((d) => without(d, b.department));
                            }}
                          />
                        ) : b.id === null ? <span className="muted">—</span> : formatMoney(b.limit)}
                      </td>
                      <td className="num">{formatMoney(b.spent)}</td>
                      <td className="num">{b.pending ? formatMoney(b.pending) : <span className="muted">—</span>}</td>
                      <td className={`num ${b.remaining < 0 ? 'text-critical' : ''}`}>
                        {b.id === null ? <span className="muted">—</span> : formatMoney(b.remaining)}
                      </td>
                      <td>
                        {b.id === null ? (
                          <span className="muted cell-sub">No limit</span>
                        ) : (
                          <div className="meter-cell">
                            <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100}
                              aria-valuenow={Math.round(b.utilization)} aria-label={`${b.department} budget used`}>
                              <div className={`meter-fill meter-fill--${tone}`} style={{ width: `${Math.min(b.utilization, 100)}%` }} />
                            </div>
                            <span>{Math.round(b.utilization)}%</span>
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`status-tag status-tag--${tone}`}>
                          <Icon size={13} aria-hidden="true" /> {statusLabel}
                        </span>
                      </td>
                      {canManage && (
                        <td className="num">
                          <div className="approval-actions">
                            <button
                              className="icon-btn icon-btn--approve"
                              aria-label={`Save ${b.department} budget`}
                              title="Save (Enter)"
                              disabled={!dirty || !valid || busy}
                              onClick={() => save.mutate({ dept: b.department, limit: draftNum })}
                            >
                              {busy && save.isPending ? <span className="spinner" aria-hidden="true" /> : <Save size={15} />}
                            </button>
                            <button
                              className="icon-btn icon-btn--reject"
                              aria-label={`Remove ${b.department} budget`}
                              title="Remove budget"
                              disabled={b.id === null || busy}
                              onClick={() => {
                                if (window.confirm(`Remove the ${b.department} budget for ${label}?`)) remove.mutate(b);
                              }}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
