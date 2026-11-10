'use client';
import { FormEvent, useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Paperclip, Search, X } from 'lucide-react';

import { expensesApi } from '@/lib/api/finance';
import { DEPARTMENTS, EXPENSE_CATEGORIES } from '@/lib/constants/finance';
import { formatMoney, formatShortDate } from '@/lib/format';
import { canApprove, useCurrentUser } from '@/hooks/useCurrentUser';
import { useRefreshFinance, useToast } from '@/hooks/useFinance';
import { Expense, ExpenseQuery, ExpenseSort } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ExpensesTable, useDebounced } from '@/components/dashboard/ExpensesTable';
import { ExpenseDetailModal } from '@/components/expenses/ExpenseDetailModal';

const PAGE_SIZE = 20;
const STALE_DAYS = 5;

type Tab = 'queue' | 'approved' | 'rejected';

const SORTS: { value: ExpenseSort; label: string }[] = [
  { value: 'date', label: 'Oldest first' },
  { value: '-date', label: 'Newest first' },
  { value: '-amount', label: 'Largest first' },
  { value: 'amount', label: 'Smallest first' },
];

function daysWaiting(e: Expense) {
  if (!e.submitted_at) return 0;
  return Math.floor((Date.now() - new Date(e.submitted_at).getTime()) / 86_400_000);
}

export function ApprovalsView() {
  const { user } = useCurrentUser();
  const approver = canApprove(user);
  const [tab, setTab] = useState<Tab>('queue');
  const [selected, setSelected] = useState<number | null>(null);
  const { flash, toastNode } = useToast();

  return (
    <div className="dashboard">
      <div className="page-head">
        <div>
          <h1>Approvals</h1>
          <p className="muted">
            {approver
              ? user?.department && !user.roles.some((r) => r === 'FINANCE_ADMIN' || r === 'SYSTEM_ADMIN')
                ? `Review expenses submitted by the ${user.department} team.`
                : 'Review expenses submitted across the company.'
              : 'Track your submitted expenses while they wait for a manager or finance admin.'}
          </p>
        </div>
      </div>

      {toastNode}

      <div className="tabs" role="tablist" aria-label="Approval views">
        {([
          ['queue', approver ? 'Needs review' : 'Waiting'],
          ['approved', 'Approved'],
          ['rejected', 'Rejected'],
        ] as [Tab, string][]).map(([value, label]) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            className={`tab ${tab === value ? 'is-active' : ''}`}
            onClick={() => setTab(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'queue' ? (
        <ReviewQueue onOpen={setSelected} flash={flash} />
      ) : (
        <section className="card">
          {user && (
            <ExpensesTable
              status={tab}
              pageSize={15}
              onSelect={(e) => setSelected(e.id)}
              onError={(m) => flash(m, 'error')}
            />
          )}
        </section>
      )}

      <ExpenseDetailModal expenseId={selected} onClose={() => setSelected(null)} onChanged={flash} />
    </div>
  );
}

function ReviewQueue({
  onOpen, flash,
}: { onOpen: (id: number) => void; flash: (m: string, t?: 'success' | 'error') => void }) {
  const { user } = useCurrentUser();
  const refresh = useRefreshFinance();
  const [query, setQuery] = useState('');
  const [department, setDepartment] = useState('all');
  const [category, setCategory] = useState('all');
  const [sort, setSort] = useState<ExpenseSort>('date');
  const [page, setPage] = useState(1);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const search = useDebounced(query.trim());

  const params: ExpenseQuery = {
    status: 'pending',
    search: search || undefined,
    department: department === 'all' ? undefined : department,
    category: category === 'all' ? undefined : category,
    sort,
    page,
    page_size: PAGE_SIZE,
  };

  const { data, isPending, isError, error, isFetching } = useQuery({
    queryKey: ['expenses', 'queue', params],
    queryFn: () => expensesApi.list(params),
    placeholderData: keepPreviousData,
    enabled: !!user,
  });

  const rows = data?.items ?? [];
  const reviewable = rows.filter((e) => e.can_review);
  const pickedRows = rows.filter((e) => picked.has(e.id));
  const pickedTotal = pickedRows.reduce((s, e) => s + e.amount, 0);
  const allPicked = reviewable.length > 0 && reviewable.every((e) => picked.has(e.id));

  function change<T>(set: (v: T) => void) {
    return (v: T) => {
      set(v);
      setPage(1);
      setPicked(new Set());
    };
  }

  function goTo(p: number) {
    setPage(p);
    setPicked(new Set());   // selection is per page
  }

  function toggle(id: number) {
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setPicked(allPicked ? new Set() : new Set(reviewable.map((e) => e.id)));
  }

  const decide = useMutation({
    mutationFn: ({ ids, action, reason }: { ids: number[]; action: 'approve' | 'reject'; reason?: string }) =>
      expensesApi.bulkDecision(ids, action, reason),
    onSuccess: async (res, vars) => {
      const verb = vars.action === 'approve' ? 'Approved' : 'Rejected';
      if (res.failed.length === 0) {
        flash(`${verb} ${res.succeeded.length} expense${res.succeeded.length === 1 ? '' : 's'}.`);
      } else {
        flash(
          `${verb} ${res.succeeded.length}; ${res.failed.length} failed: ${res.failed[0].message}`,
          'error',
        );
      }
      setPicked(new Set());
      setRejecting(false);
      setReason('');
      await refresh();
    },
    onError: (e: Error) => flash(e.message, 'error'),
  });

  function bulkReject(ev: FormEvent) {
    ev.preventDefault();
    if (reason.trim().length < 3) return;
    decide.mutate({ ids: [...picked], action: 'reject', reason: reason.trim() });
  }

  const total = data?.total ?? 0;
  const pageCount = data?.pages ?? 1;

  return (
    <section className="card">
      <div className="table-toolbar">
        <label className="search-field">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search pending expenses</span>
          <input
            type="search"
            placeholder="Search merchant, person, EXP-…"
            value={query}
            onChange={(e) => change(setQuery)(e.target.value)}
          />
        </label>
        <label className="select-field">
          <span className="sr-only">Department</span>
          <select value={department} onChange={(e) => change(setDepartment)(e.target.value)}>
            <option value="all">All departments</option>
            {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="select-field">
          <span className="sr-only">Category</span>
          <select value={category} onChange={(e) => change(setCategory)(e.target.value)}>
            <option value="all">All categories</option>
            {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="select-field">
          <span className="sr-only">Sort</span>
          <select value={sort} onChange={(e) => change(setSort)(e.target.value as ExpenseSort)}>
            {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
      </div>

      {picked.size > 0 && (
        <div className="bulk-bar" role="region" aria-label="Bulk actions">
          <span>
            <strong>{picked.size}</strong> selected · {formatMoney(pickedTotal)}
          </span>
          {rejecting ? (
            <form onSubmit={bulkReject} className="inline-form">
              <label className="sr-only" htmlFor="bulk-reason">Reason for rejecting</label>
              <input
                id="bulk-reason"
                className="field-input"
                placeholder="Reason (shown to each submitter)"
                value={reason}
                maxLength={500}
                autoFocus
                onChange={(e) => setReason(e.target.value)}
              />
              <Button type="button" variant="ghost" className="btn--sm" onClick={() => setRejecting(false)}>
                Cancel
              </Button>
              <Button type="submit" className="btn--sm" loading={decide.isPending} disabled={reason.trim().length < 3}>
                Reject {picked.size}
              </Button>
            </form>
          ) : (
            <div className="action-group">
              <Button variant="ghost" className="btn--sm" onClick={() => setPicked(new Set())}>Clear</Button>
              <Button variant="ghost" className="btn--sm" onClick={() => setRejecting(true)} disabled={decide.isPending}>
                <X size={15} aria-hidden="true" /> Reject
              </Button>
              <Button
                className="btn--sm"
                loading={decide.isPending}
                onClick={() => decide.mutate({ ids: [...picked], action: 'approve' })}
              >
                <Check size={15} aria-hidden="true" /> Approve {picked.size}
              </Button>
            </div>
          )}
        </div>
      )}

      {isError && <Alert type="error">Couldn’t load the queue: {(error as Error).message}</Alert>}

      <div className="table-wrap" aria-busy={isFetching} style={{ opacity: isFetching && !isPending ? 0.6 : 1 }}>
        <table className="data-table data-table--clickable">
          <thead>
            <tr>
              <th className="check-col">
                <input
                  type="checkbox"
                  aria-label="Select all reviewable on this page"
                  checked={allPicked}
                  disabled={reviewable.length === 0}
                  onChange={toggleAll}
                />
              </th>
              <th>Waiting</th>
              <th>Merchant</th>
              <th>Submitted by</th>
              <th>Category</th>
              <th>Receipt</th>
              <th className="num">Amount</th>
              <th className="num"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {isPending ? (
              <tr><td colSpan={8} className="empty">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={8} className="empty">Nothing waiting for review. 🎉</td></tr>
            ) : (
              rows.map((e) => {
                const days = daysWaiting(e);
                const busy = decide.isPending && decide.variables?.ids.includes(e.id);
                return (
                  <tr key={e.id} onClick={() => onOpen(e.id)} tabIndex={0}
                    onKeyDown={(ev) => { if (ev.key === 'Enter') onOpen(e.id); }}
                    className={picked.has(e.id) ? 'is-picked' : ''}>
                    <td className="check-col" onClick={(ev) => ev.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`Select ${e.reference}`}
                        checked={picked.has(e.id)}
                        disabled={!e.can_review}
                        title={e.can_review ? undefined : 'You can’t review this one (e.g. it’s your own)'}
                        onChange={() => toggle(e.id)}
                      />
                    </td>
                    <td className="nowrap">
                      <span className={days >= STALE_DAYS ? 'age age--stale' : 'age'}>
                        {days === 0 ? 'Today' : `${days}d`}
                      </span>
                      <span className="cell-sub">{formatShortDate(e.expense_date)}</span>
                    </td>
                    <td>
                      <span className="cell-main">{e.merchant}</span>
                      <span className="cell-sub">{e.reference}</span>
                    </td>
                    <td>
                      <span className="cell-main">{e.submitted_by}</span>
                      <span className="cell-sub">{e.department}</span>
                    </td>
                    <td>{e.category}</td>
                    <td>
                      {e.has_receipt ? (
                        <span className="status-tag status-tag--good"><Paperclip size={12} aria-hidden="true" /> Yes</span>
                      ) : (
                        <span className="status-tag status-tag--warning">Missing</span>
                      )}
                    </td>
                    <td className="num">{formatMoney(e.amount)}</td>
                    <td className="num" onClick={(ev) => ev.stopPropagation()}>
                      {e.can_review ? (
                        <div className="approval-actions">
                          <button
                            className="icon-btn icon-btn--reject"
                            aria-label={`Reject ${e.reference}`}
                            title="Reject (opens details to add a reason)"
                            onClick={() => onOpen(e.id)}
                            disabled={busy}
                          >
                            <X size={16} />
                          </button>
                          <button
                            className="icon-btn icon-btn--approve"
                            aria-label={`Approve ${e.reference}`}
                            title="Approve"
                            onClick={() => decide.mutate({ ids: [e.id], action: 'approve' })}
                            disabled={busy}
                          >
                            {busy ? <span className="spinner" aria-hidden="true" /> : <Check size={16} />}
                          </button>
                        </div>
                      ) : (
                        <span className="muted cell-sub">{e.submitted_by_id === user?.id ? 'Yours' : '—'}</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span className="muted">
          {total === 0 ? '0 waiting' : `${total} waiting · expenses older than ${STALE_DAYS} days are highlighted`}
        </span>
        <div className="pager">
          <button className="icon-btn" onClick={() => goTo(page - 1)} disabled={page <= 1} aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <span className="muted">Page {page} / {pageCount}</span>
          <button className="icon-btn" onClick={() => goTo(page + 1)} disabled={page >= pageCount} aria-label="Next page">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}
