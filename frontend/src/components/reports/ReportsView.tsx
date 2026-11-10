'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Info, Printer, Sparkles, TriangleAlert } from 'lucide-react';

import { analyticsApi, expensesApi } from '@/lib/api/finance';
import { PERIODS } from '@/lib/constants/finance';
import { formatMoney, formatMoneyCompact } from '@/lib/format';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useToast } from '@/hooks/useFinance';
import { ExpenseStatus, Period } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { KpiCards } from '@/components/dashboard/KpiCards';
import { SpendingChart } from '@/components/dashboard/SpendingChart';
import { CategoryBreakdown } from '@/components/dashboard/CategoryBreakdown';

const SCOPE_TEXT = {
  company: 'Company-wide figures',
  department: 'Figures for your department',
  personal: 'Figures for your own expenses',
} as const;

const fullDate = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const fmtDate = (iso: string) => fullDate.format(new Date(`${iso}T00:00:00`));

function HBars({ rows }: { rows: { label: string; amount: number }[] }) {
  if (rows.length === 0) return <p className="empty">No spend in this period.</p>;
  const max = Math.max(...rows.map((r) => r.amount), 1);
  const total = rows.reduce((s, r) => s + r.amount, 0);
  return (
    <ul className="hbar-list">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="hbar-row">
            <span>{r.label}</span>
            <span className="hbar-value">
              {formatMoney(r.amount)}
              <span className="muted"> · {total ? Math.round((r.amount / total) * 100) : 0}%</span>
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(r.amount / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ReportsView() {
  const { user } = useCurrentUser();
  const [period, setPeriod] = useState<Period>('quarter');
  const [exportStatus, setExportStatus] = useState<ExpenseStatus | 'all'>('approved');
  const [exporting, setExporting] = useState(false);
  const { flash, toastNode } = useToast();

  const summary = useQuery({
    queryKey: ['analytics', 'summary', period],
    queryFn: () => analyticsApi.summary(period),
    enabled: !!user,
  });

  const s = summary.data;
  const months = PERIODS.find((p) => p.value === period)!.months;

  async function exportCsv() {
    if (!s) return;
    setExporting(true);
    try {
      await expensesApi.exportCsv({
        date_from: s.range.start,
        date_to: s.range.end,
        status: exportStatus === 'all' ? undefined : exportStatus,
        sort: 'date',
      });
    } catch (e) {
      flash((e as Error).message, 'error');
    } finally {
      setExporting(false);
    }
  }

  const kpis = !s
    ? ['Total spend', 'Expenses', 'Average expense', 'Previous period'].map((label) => ({
        label, value: summary.isPending ? '…' : '—', detail: '',
      }))
    : [
        {
          label: 'Total spend',
          value: formatMoneyCompact(s.kpis.total_spend),
          delta: s.kpis.change_pct ?? undefined,
          detail: s.kpis.change_pct !== null ? 'vs previous period' : 'Approved + pending',
        },
        {
          label: 'Expenses',
          value: String(s.kpis.expense_count),
          detail: `${s.kpis.pending_count} still pending review`,
        },
        {
          label: 'Average expense',
          value: formatMoney(s.kpis.average_expense),
          detail: `${s.top_merchants.length ? `Top merchant: ${s.top_merchants[0].merchant}` : 'No merchants yet'}`,
        },
        {
          label: 'Previous period',
          value: formatMoneyCompact(s.kpis.previous_spend),
          detail: 'Same length, immediately before',
        },
      ];

  return (
    <div className="dashboard report">
      <div className="page-head">
        <div>
          <h1>Reports</h1>
          <p className="muted">
            {s
              ? `${SCOPE_TEXT[s.scope]} · ${fmtDate(s.range.start)} – ${fmtDate(s.range.end)} · approved + pending spend`
              : 'Spending analysis for the selected period.'}
          </p>
        </div>
        <div className="page-head-actions no-print">
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
          <button className="btn btn--ghost btn--sm" onClick={() => window.print()}>
            <Printer size={15} aria-hidden="true" /> Print
          </button>
        </div>
      </div>

      {toastNode}
      {summary.isError && <Alert type="error">Couldn’t load the report: {(summary.error as Error).message}</Alert>}

      <KpiCards items={kpis} />

      <div className="grid-2-1">
        <section className="card">
          <div className="card-head">
            <h2>12-month trend</h2>
            <span className="muted cell-sub">Selected period highlighted</span>
          </div>
          {s ? <SpendingChart data={s.monthly} highlightLast={months} /> : <p className="empty">Loading…</p>}
        </section>

        <section className="card">
          <div className="card-head"><h2>By department</h2></div>
          <HBars rows={(s?.by_department ?? []).map((d) => ({ label: d.department, amount: d.amount }))} />
        </section>
      </div>

      <div className="grid-3">
        <section className="card">
          <div className="card-head"><h2>By category</h2></div>
          <CategoryBreakdown rows={s?.by_category ?? []} />
        </section>

        <section className="card">
          <div className="card-head"><h2>Top merchants</h2></div>
          {s && s.top_merchants.length > 0 ? (
            <table className="data-table data-table--compact">
              <thead>
                <tr><th>Merchant</th><th className="num">Count</th><th className="num">Spend</th></tr>
              </thead>
              <tbody>
                {s.top_merchants.map((m) => (
                  <tr key={m.merchant}>
                    <td>{m.merchant}</td>
                    <td className="num">{m.count}</td>
                    <td className="num">{formatMoney(m.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty">{summary.isPending ? 'Loading…' : 'No spend in this period.'}</p>
          )}
        </section>

        <section className="card">
          <div className="card-head"><h2><Sparkles size={16} aria-hidden="true" /> Insights</h2></div>
          {s && s.insights.length === 0 && <p className="empty">Nothing unusual spotted.</p>}
          <ul className="insight-list">
            {(s?.insights ?? []).map((ins) => (
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

      <section className="card no-print">
        <div className="card-head">
          <h2><Download size={16} aria-hidden="true" /> Export</h2>
        </div>
        <div className="export-row">
          <p className="muted">
            Download every expense dated {s ? `${fmtDate(s.range.start)} – ${fmtDate(s.range.end)}` : 'in this period'} as
            CSV, ready for Excel or your accounting system.
          </p>
          <label className="select-field">
            <span className="sr-only">Statuses to export</span>
            <select value={exportStatus} onChange={(e) => setExportStatus(e.target.value as ExpenseStatus | 'all')}>
              <option value="approved">Approved only</option>
              <option value="pending">Pending only</option>
              <option value="rejected">Rejected only</option>
              <option value="all">All statuses</option>
            </select>
          </label>
          <Button className="btn--sm" onClick={exportCsv} loading={exporting} disabled={!s}>
            <Download size={15} aria-hidden="true" /> Download CSV
          </Button>
        </div>
      </section>
    </div>
  );
}
