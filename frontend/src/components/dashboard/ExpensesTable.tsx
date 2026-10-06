'use client';
import { useMemo, useState } from 'react';
import { ArrowUpDown, ChevronLeft, ChevronRight, Download, Paperclip, Search } from 'lucide-react';
import { EXPENSE_CATEGORIES, Expense, ExpenseStatus } from '@/lib/mock/dashboard';
import { formatMoney, formatShortDate } from '@/lib/format';

const PAGE_SIZE = 6;
const STATUSES: ExpenseStatus[] = ['pending', 'approved', 'rejected', 'draft'];

type SortKey = 'date' | 'amount';

function toCsv(rows: Expense[]) {
  const header = ['ID', 'Date', 'Merchant', 'Category', 'Department', 'Submitted by', 'Amount', 'Status', 'Receipt'];
  const escape = (v: string | number | boolean) => `"${String(v).replace(/"/g, '""')}"`;
  const lines = rows.map((e) =>
    [e.id, e.date, e.merchant, e.category, e.department, e.submittedBy, e.amount.toFixed(2), e.status, e.hasReceipt ? 'yes' : 'no']
      .map(escape)
      .join(','),
  );
  return [header.map(escape).join(','), ...lines].join('\n');
}

function downloadCsv(rows: Expense[]) {
  const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `expenses-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function ExpensesTable({ expenses }: { expenses: Expense[] }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<ExpenseStatus | 'all'>('all');
  const [category, setCategory] = useState<string>('all');
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'date', dir: 'desc' });
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = expenses.filter((e) =>
      (status === 'all' || e.status === status) &&
      (category === 'all' || e.category === category) &&
      (!q || [e.id, e.merchant, e.submittedBy, e.department].some((f) => f.toLowerCase().includes(q))),
    );
    const mult = sort.dir === 'asc' ? 1 : -1;
    return rows.sort((a, b) =>
      sort.key === 'amount' ? (a.amount - b.amount) * mult : a.date.localeCompare(b.date) * mult,
    );
  }, [expenses, query, status, category, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  function toggleSort(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }));
  }

  // Any filter change jumps back to the first page
  function withReset<T>(set: (v: T) => void) {
    return (v: T) => {
      set(v);
      setPage(0);
    };
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
            placeholder="Search merchant, person, ID…"
            value={query}
            onChange={(e) => withReset(setQuery)(e.target.value)}
          />
        </label>

        <label className="select-field">
          <span className="sr-only">Status</span>
          <select value={status} onChange={(e) => withReset(setStatus)(e.target.value as ExpenseStatus | 'all')}>
            <option value="all">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </label>

        <label className="select-field">
          <span className="sr-only">Category</span>
          <select value={category} onChange={(e) => withReset(setCategory)(e.target.value)}>
            <option value="all">All categories</option>
            {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>

        <button
          className="btn btn--ghost btn--sm"
          onClick={() => downloadCsv(filtered)}
          disabled={filtered.length === 0}
        >
          <Download size={15} aria-hidden="true" />
          Export CSV
        </button>
      </div>

      <div className="table-wrap">
        <table className="data-table">
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
            {visible.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">No expenses match these filters.</td>
              </tr>
            ) : (
              visible.map((e) => (
                <tr key={e.id}>
                  <td className="nowrap">{formatShortDate(e.date)}</td>
                  <td>
                    <span className="cell-main">
                      {e.merchant}
                      {e.hasReceipt && <Paperclip size={12} aria-label="Receipt attached" />}
                    </span>
                    <span className="cell-sub">{e.id}</span>
                  </td>
                  <td>{e.category}</td>
                  <td>
                    <span className="cell-main">{e.submittedBy}</span>
                    <span className="cell-sub">{e.department}</span>
                  </td>
                  <td><span className={`pill pill--${e.status}`}>{e.status}</span></td>
                  <td className="num">{formatMoney(e.amount)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span className="muted">
          {filtered.length === 0
            ? '0 results'
            : `${currentPage * PAGE_SIZE + 1}–${currentPage * PAGE_SIZE + visible.length} of ${filtered.length}`}
        </span>
        <div className="pager">
          <button
            className="icon-btn"
            onClick={() => setPage(currentPage - 1)}
            disabled={currentPage === 0}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="muted">Page {currentPage + 1} / {pageCount}</span>
          <button
            className="icon-btn"
            onClick={() => setPage(currentPage + 1)}
            disabled={currentPage >= pageCount - 1}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
