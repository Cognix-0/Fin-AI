import { CircleCheck, OctagonAlert, TriangleAlert } from 'lucide-react';
import { Budget } from '@/lib/mock/dashboard';
import { formatMoney } from '@/lib/format';

function budgetStatus(pct: number) {
  if (pct > 100) return { tone: 'critical', label: 'Over budget', Icon: OctagonAlert };
  if (pct >= 85) return { tone: 'warning', label: 'Near limit', Icon: TriangleAlert };
  return { tone: 'good', label: 'On track', Icon: CircleCheck };
}

export function BudgetList({ budgets }: { budgets: Budget[] }) {
  return (
    <ul className="budget-list">
      {budgets.map((b) => {
        const pct = (b.spent / b.limit) * 100;
        const { tone, label, Icon } = budgetStatus(pct);
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
              {formatMoney(b.spent)} of {formatMoney(b.limit)} · {Math.round(pct)}%
            </p>
          </li>
        );
      })}
    </ul>
  );
}
