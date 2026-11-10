'use client';
import { FormEvent, useState } from 'react';
import { Check, Paperclip, X } from 'lucide-react';
import { Expense } from '@/types/finance';
import { formatMoney, formatShortDate } from '@/lib/format';
import { expensesApi } from '@/lib/api/finance';

interface Props {
  expenses: Expense[];      // already filtered to pending
  busyId: number | null;    // expense currently being approved/rejected
  onApprove: (e: Expense) => void;
  onReject: (e: Expense, reason: string) => void;
}

export function PendingApprovals({ expenses, busyId, onApprove, onReject }: Props) {
  // Which item has its "reason for rejection" form open
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [reason, setReason] = useState('');

  if (expenses.length === 0) {
    return <p className="empty">Nothing waiting for review. 🎉</p>;
  }

  function submitReject(ev: FormEvent, e: Expense) {
    ev.preventDefault();
    if (reason.trim().length < 3) return;
    onReject(e, reason.trim());
    setRejecting(null);
    setReason('');
  }

  return (
    <ul className="approval-list">
      {expenses.map((e) => {
        const busy = busyId === e.id;
        return (
          <li key={e.id} className="approval-item" style={{ flexWrap: 'wrap' }}>
            <div className="approval-main">
              <p className="approval-title">
                {e.merchant}
                {e.has_receipt ? (
                  <button
                    type="button"
                    className="status-tag status-tag--good"
                    onClick={() => expensesApi.openReceipt(e.id).catch(() => {})}
                    title={`Open ${e.receipt_filename ?? 'receipt'}`}
                    style={{ cursor: 'pointer', border: 0 }}
                  >
                    <Paperclip size={12} aria-hidden="true" /> Receipt
                  </button>
                ) : (
                  <span className="status-tag status-tag--warning" title="No receipt attached">
                    <Paperclip size={12} aria-hidden="true" /> No receipt
                  </span>
                )}
              </p>
              <p className="muted">
                {e.submitted_by} · {e.department} · {formatShortDate(e.expense_date)} · {e.reference}
              </p>
            </div>
            <div className="approval-side">
              <span className="approval-amount">{formatMoney(e.amount)}</span>
              {e.can_review && (
                <div className="approval-actions">
                  <button
                    className="icon-btn icon-btn--reject"
                    onClick={() => {
                      setRejecting(rejecting === e.id ? null : e.id);
                      setReason('');
                    }}
                    disabled={busy}
                    aria-expanded={rejecting === e.id}
                    aria-label={`Reject ${e.reference} from ${e.merchant}`}
                    title="Reject"
                  >
                    <X size={16} />
                  </button>
                  <button
                    className="icon-btn icon-btn--approve"
                    onClick={() => onApprove(e)}
                    disabled={busy}
                    aria-label={`Approve ${e.reference} from ${e.merchant}`}
                    title="Approve"
                  >
                    {busy ? <span className="spinner" aria-hidden="true" /> : <Check size={16} />}
                  </button>
                </div>
              )}
            </div>

            {rejecting === e.id && (
              <form
                onSubmit={(ev) => submitReject(ev, e)}
                style={{ display: 'flex', gap: 8, width: '100%', marginTop: 8 }}
              >
                <label className="sr-only" htmlFor={`reason-${e.id}`}>Reason for rejecting {e.reference}</label>
                <input
                  id={`reason-${e.id}`}
                  className="field-input"
                  placeholder="Reason (shown to the submitter)"
                  value={reason}
                  maxLength={500}
                  onChange={(ev) => setReason(ev.target.value)}
                  autoFocus
                  style={{ flex: 1 }}
                />
                <button className="btn btn--primary btn--sm" type="submit" disabled={reason.trim().length < 3}>
                  Reject
                </button>
              </form>
            )}
          </li>
        );
      })}
    </ul>
  );
}
