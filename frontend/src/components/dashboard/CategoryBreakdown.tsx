import { formatMoney } from '@/lib/format';

interface Row {
  category: string;
  amount: number;
  share: number;       // % of the period total
}

export function CategoryBreakdown({ rows }: { rows: Row[] }) {
  if (rows.length === 0) {
    return <p className="empty">No expenses to break down yet.</p>;
  }
  const max = rows[0].amount;   // rows arrive sorted, largest first

  return (
    <ul className="hbar-list">
      {rows.map(({ category, amount, share }) => (
        <li key={category} title={`${category}: ${formatMoney(amount)}`}>
          <div className="hbar-row">
            <span>{category}</span>
            <span className="hbar-value">
              {formatMoney(amount)}
              <span className="muted"> · {Math.round(share)}%</span>
            </span>
          </div>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${max ? (amount / max) * 100 : 0}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
