'use client';
import { Check, Paperclip, X } from 'lucide-react';
import { Expense } from '@/lib/mock/dashboard';
import { formatMoney, formatShortDate } from '@/lib/format';

interface Props {
  expenses: Expense[];      // already filtered to pending
  canApprove: boolean;
  onDecision: (id: string, status: 'approved' | 'rejected') => void;
}

export function PendingApprovals({ expenses, canApprove, onDecision }: Props) {
  if (expenses.length === 0) {
    return <p className="empty">Nothing waiting for review. 🎉</p>;
  }

  return (
    <ul className="approval-list">
      {expenses.map((e) => (
        <li key={e.id} className="approval-item">
          <div className="approval-main">
            <p className="approval-title">
              {e.merchant}
              {!e.hasReceipt && (
                <span className="status-tag status-tag--warning" title="No receipt attached">
                  <Paperclip size={12} aria-hidden="true" /> No receipt
                </span>
              )}
            </p>
            <p className="muted">
              {e.submittedBy} · {e.department} · {formatShortDate(e.date)}
            </p>
          </div>
          <div className="approval-side">
            <span className="approval-amount">{formatMoney(e.amount)}</span>
            {canApprove && (
              <div className="approval-actions">
                <button
                  className="icon-btn icon-btn--reject"
                  onClick={() => onDecision(e.id, 'rejected')}
                  aria-label={`Reject ${e.id} from ${e.merchant}`}
                  title="Reject"
                >
                  <X size={16} />
                </button>
                <button
                  className="icon-btn icon-btn--approve"
                  onClick={() => onDecision(e.id, 'approved')}
                  aria-label={`Approve ${e.id} from ${e.merchant}`}
                  title="Approve"
                >
                  <Check size={16} />
                </button>
              </div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
