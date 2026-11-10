'use client';
import { useEffect, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Paperclip, Search, X } from 'lucide-react';

import { DEPARTMENTS, EXPENSE_CATEGORIES, EXPENSE_STATUSES } from '@/lib/constants/finance';
import { expensesApi } from '@/lib/api/finance';
import { formatMoney, formatShortDate } from '@/lib/format';
import { Expense, ExpenseQuery, ExpenseSort, ExpenseStatus } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';

type SortKey = 'date' | 'amount';

export function useDebounced<T>(value: T, ms = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

interface Props {
  onError: (message: string) => void;
  /** Clicking a row opens it (e.g. in ExpenseDetailModal). */
  onSelect?: (e: Expense) => void;
  /** Extra filters: department, date range, missing receipt. */
  advanced?: boolean;
  pageSize?: number;
  /** Status chosen outside the table (e.g. by tabs); hides the status dropdown. */
  status?: ExpenseStatus | 'all';
  defaultMine?: boolean;
}

export function ExpensesTable({
  onError, onSelect, advanced = false, pageSize = 8, status: externalStatus, defaultMine = false,
}: Props) {
  const [query, setQuery] = useState('');
  const [ownStatus, setStatus] = useState<ExpenseStatus | 'all'>('all');
  const [category, setCategory] = useState<string>('all');
  const [department, setDepartment] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [missingReceipt, setMissingReceipt] = useState(false);
  const [mine, setMine] = useState(defaultMine);
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'date', dir: 'desc' });
  const [page, setPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const search = useDebounced(query.trim());

  const status = externalStatus ?? ownStatus;
  // Tabs changing the status should also go back to page 1
  const [prevExternal, setPrevExternal] = useState(externalStatus);
  if (prevExternal !== externalStatus) {
    setPrevExternal(externalStatus);
    setPage(1);
  }

  const params: ExpenseQuery = {
    search: search || undefined,
    status: status === 'all' ? undefined : status,
    category: category === 'all' ? undefined : category,
    department: advanced && department !== 'all' ? department : undefined,
    date_from: advanced && dateFrom ? dateFrom : undefined,
    date_to: advanced && dateTo ? dateTo : undefined,
    missing_receipt: advanced && missingReceipt ? true : undefined,
    mine: mine || undefined,
    sort: `${sort.dir === 'desc' ? '-' : ''}${sort.key}` as ExpenseSort,
    page,
    page_size: pageSize,
  };

  const { data, isPending, isError, error, isFetching } = useQuery({
    queryKey: ['expenses', 'table', params],
    queryFn: () => expensesApi.list(params),
    placeholderData: keepPreviousData,   // keep rows on screen while the next page loads
  });

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = data?.pages ?? 1;
  const filtered = Boolean(
    search || category !== 'all' || mine || (advanced && (department !== 'all' || dateFrom || dateTo || missingReceipt)),
  );

  function toggleSort(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }));
    setPage(1);
  }

  // Any filter change jumps back to the first page
  function withReset<T>(set: (v: T) => void) {
    return (v: T) => {
      set(v);
      setPage(1);
    };
  }

  function clearFilters() {
    setQuery('');
    setCategory('all');
    setDepartment('all');
    setDateFrom('');
    setDateTo('');
    setMissingReceipt(false);
    setMine(false);
    setPage(1);
  }

  async function exportCsv() {
    setExporting(true);
    try {
      await expensesApi.exportCsv(params);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setExporting(false);
    }
  }

  const ariaSort = (key: SortKey) =>
    sort.key === key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none';

  return (
    <div>
      <div className="table-toolbar">
        <label className="search-field">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search expenses</span>
          <input
            type="search"
            placeholder="Search merchant, person, EXP-…"
            value={query}
            onChange={(e) => withReset(setQuery)(e.target.value)}
          />
        </label>

        {externalStatus === undefined && (
          <label className="select-field">
            <span className="sr-only">Status</span>
            <select value={status} onChange={(e) => withReset(setStatus)(e.target.value as ExpenseStatus | 'all')}>
              <option value="all">All statuses</option>
              {EXPENSE_STATUSES.map((s) => (
                <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
          </label>
        )}

        <label className="select-field">
          <span className="sr-only">Category</span>
          <select value={category} onChange={(e) => withReset(setCategory)(e.target.value)}>
            <option value="all">All categories</option>
            {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>

        {advanced && (
          <label className="select-field">
            <span className="sr-only">Department</span>
            <select value={department} onChange={(e) => withReset(setDepartment)(e.target.value)}>
              <option value="all">All departments</option>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        )}

        <label className="select-field">
          <span className="sr-only">Whose expenses</span>
          <select value={mine ? 'mine' : 'all'} onChange={(e) => withReset(setMine)(e.target.value === 'mine')}>
            <option value="all">Everyone I can see</option>
            <option value="mine">Only mine</option>
          </select>
        </label>

        <button
          className="btn btn--ghost btn--sm"
          onClick={exportCsv}
          disabled={total === 0 || exporting}
          aria-busy={exporting}
        >
          {exporting ? <span className="spinner" aria-hidden="true" /> : <Download size={15} aria-hidden="true" />}
          Export CSV
        </button>
      </div>

      {advanced && (
        <div className="table-toolbar table-toolbar--sub">
          <label className="date-field">
            <span>From</span>
            <input type="date" value={dateFrom} max={dateTo || undefined}
              onChange={(e) => withReset(setDateFrom)(e.target.value)} />
          </label>
          <label className="date-field">
            <span>To</span>
            <input type="date" value={dateTo} min={dateFrom || undefined}
              onChange={(e) => withReset(setDateTo)(e.target.value)} />
          </label>
          <label className="check-field">
            <input type="checkbox" checked={missingReceipt}
              onChange={(e) => withReset(setMissingReceipt)(e.target.checked)} />
            Missing receipt only
          </label>
          {filtered && (
            <button className="link-btn" onClick={clearFilters}>
              <X size={14} aria-hidden="true" /> Clear filters
            </button>
          )}
        </div>
      )}

      {isError && <Alert type="error">Couldn’t load expenses: {(error as Error).message}</Alert>}

      <div className="table-wrap" aria-busy={isFetching} style={{ opacity: isFetching && !isPending ? 0.6 : 1 }}>
        <table className={`data-table ${onSelect ? 'data-table--clickable' : ''}`}>
          <thead>
            <tr>
              <th aria-sort={ariaSort('date')}>
                <button className="sort-btn" onClick={() => toggleSort('date')}>
                  Date <ArrowUpDown size={13} aria-hidden="true" />
                </button>
              </th>
              <th>Merchant</th>
              <th>Category</th>
              <th>Submitted by</th>
              <th>Status</th>
              <th className="num" aria-sort={ariaSort('amount')}>
                <button className="sort-btn" onClick={() => toggleSort('amount')}>
                  Amount <ArrowUpDown size={13} aria-hidden="true" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {isPending ? (
              <tr><td colSpan={6} className="empty">Loading expenses…</td></tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">
                  {filtered || status !== 'all'
                    ? 'No expenses match these filters.'
                    : 'No expenses yet — create one with “New expense”.'}
                </td>
              </tr>
            ) : (
              rows.map((e) => (
                <tr
                  key={e.id}
                  onClick={onSelect ? () => onSelect(e) : undefined}
                  onKeyDown={onSelect ? (ev) => { if (ev.key === 'Enter') onSelect(e); } : undefined}
                  tabIndex={onSelect ? 0 : undefined}
                  aria-label={onSelect ? `Open ${e.reference}` : undefined}
                >
                  <td className="nowrap">{formatShortDate(e.expense_date)}</td>
                  <td>
                    <span className="cell-main">
                      {e.merchant}
                      {e.has_receipt && (
                        <button
                          type="button"
                          className="icon-btn"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            expensesApi.openReceipt(e.id).catch((err) => onError(err.message));
                          }}
                          aria-label={`Open receipt for ${e.reference}`}
                          title="Open receipt"
                          style={{ width: 22, height: 22 }}
                        >
                          <Paperclip size={12} />
                        </button>
                      )}
                    </span>
                    <span className="cell-sub">{e.reference}</span>
                  </td>
                  <td>{e.category}</td>
                  <td>
                    <span className="cell-main">{e.submitted_by}</span>
                    <span className="cell-sub">{e.department}</span>
                  </td>
                  <td>
                    <span className={`pill pill--${e.status}`} title={e.rejection_reason ?? undefined}>
                      {e.status}
                    </span>
                    {e.status === 'rejected' && e.rejection_reason && (
                      <span className="cell-sub">{e.rejection_reason}</span>
                    )}
                  </td>
                  <td className="num">{formatMoney(e.amount)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span className="muted">
          {total === 0
            ? '0 results'
            : `${(page - 1) * pageSize + 1}–${(page - 1) * pageSize + rows.length} of ${total}`}
        </span>
        <div className="pager">
          <button
            className="icon-btn"
            onClick={() => setPage((p) => p - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="muted">Page {page} / {pageCount}</span>
          <button
            className="icon-btn"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= pageCount}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
