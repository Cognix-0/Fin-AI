import { Expense } from '@/lib/mock/dashboard';
import { formatMoney } from '@/lib/format';

export function CategoryBreakdown({ expenses }: { expenses: Expense[] }) {
  const totals = new Map<string, number>();
  for (const e of expenses) {
    if (e.status === 'rejected') continue;
    totals.set(e.category, (totals.get(e.category) ?? 0) + e.amount);
  }
  const rows = [...totals.entries()].sort((a, b) => b[1] - a[1]);
  const max = rows[0]?.[1] ?? 0;
  const total = rows.reduce((s, [, v]) => s + v, 0);

  if (rows.length === 0) {
    return <p className="empty">No expenses to break down yet.</p>;
  }

  return (
    <ul className="hbar-list">
      {rows.map(([category, amount]) => (
        <li key={category} title={`${category}: ${formatMoney(amount)}`}>
          <div className="hbar-row">
            <span>{category}</span>
            <span className="hbar-value">
              {formatMoney(amount)}
              <span className="muted"> · {Math.round((amount / total) * 100)}%</span>
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(amount / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
