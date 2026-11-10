import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-react';
import { Budget, BudgetStatus } from '@/types/finance';
import { formatMoney } from '@/lib/format';

// Status is computed server-side from approved + pending ("committed") spend
const STATUS = {
  over_budget: { tone: 'critical', label: 'Over budget', Icon: OctagonAlert },
  near_limit: { tone: 'warning', label: 'Near limit', Icon: TriangleAlert },
  on_track: { tone: 'good', label: 'On track', Icon: CircleCheck },
  no_budget: { tone: 'good', label: 'No budget', Icon: CircleCheck },
} satisfies Record<BudgetStatus, unknown>;

export function BudgetList({ budgets }: { budgets: Budget[] }) {
  if (budgets.length === 0) {
    return <p className="empty">No budgets set for this month yet.</p>;
  }
  return (
    <ul className="budget-list">
      {budgets.map((b) => {
        const pct = b.utilization;
        const { tone, label, Icon } = STATUS[b.status];
        return (
          <li key={b.department}>
            <div className="budget-row">
              <span className="budget-name">{b.department}</span>
              <span className={`status-tag status-tag--${tone}`}>
                <Icon size={13} aria-hidden="true" />
                {label}
              </span>
            </div>
            <div
              className="meter"
              role="meter"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(pct)}
              aria-label={`${b.department} budget used`}
            >
              <div className={`meter-fill meter-fill--${tone}`} style={{ width: `${Math.min(pct, 100)}%` }} />
            </div>
            <p className="budget-meta">
              {formatMoney(b.spent + b.pending)} of {formatMoney(b.limit)} · {Math.round(pct)}%
              {b.pending > 0 && <span className="muted"> · {formatMoney(b.pending)} pending</span>}
            </p>
          </li>
        );
      })}
    </ul>
  );
}
