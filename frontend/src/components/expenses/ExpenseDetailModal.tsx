'use client';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Check, Clock, Paperclip, Pencil, Send, Trash2, Undo2, Upload, X,
} from 'lucide-react';

import { expensesApi } from '@/lib/api/finance';
import { DEPARTMENTS, EXPENSE_CATEGORIES } from '@/lib/constants/finance';
import { ExpenseFormValues, expenseSchema } from '@/lib/validation/expense';
import { formatMoney } from '@/lib/format';
import { useCurrentUser } from '@/hooks/useCurrentUser';
import { useRefreshFinance } from '@/hooks/useFinance';
import { Expense } from '@/types/finance';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

const RECEIPT_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'application/pdf'];
const MAX_RECEIPT_BYTES = 10 * 1024 * 1024;

const dateTime = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
});
const longDate = new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

const ACTION_TEXT: Record<string, string> = {
  created: 'Created',
  updated: 'Edited',
  submitted: 'Submitted for approval',
  withdrawn: 'Withdrawn to draft',
  approved: 'Approved',
  rejected: 'Rejected',
  receipt_added: 'Receipt attached',
  receipt_replaced: 'Receipt replaced',
  receipt_removed: 'Receipt removed',
};

interface Props {
  expenseId: number | null;
  onClose: () => void;
  /** Called after any successful change with a message for the page's toast. */
  onChanged: (message: string, type?: 'success' | 'error') => void;
}

export function ExpenseDetailModal({ expenseId, onClose, onChanged }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const { user } = useCurrentUser();
  const refresh = useRefreshFinance();
  const [editing, setEditing] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = expenseId !== null;

  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
    // Fresh state every time a different expense is opened
    setEditing(false);
    setRejecting(false);
    setReason('');
    setConfirmDelete(false);
    setError(null);
  }, [open, expenseId]);

  const expense = useQuery({
    queryKey: ['expense', expenseId],
    queryFn: () => expensesApi.get(expenseId!),
    enabled: open,
  });
  const history = useQuery({
    queryKey: ['expense', expenseId, 'history'],
    queryFn: () => expensesApi.history(expenseId!),
    enabled: open,
  });

  const action = useMutation({
    mutationFn: async (fn: () => Promise<unknown>) => fn(),
    onMutate: () => setError(null),
    onError: (e: Error) => setError(e.message),
  });

  async function run(fn: () => Promise<unknown>, message: string, closeAfter = false) {
    try {
      await action.mutateAsync(fn);
    } catch {
      return; // error already shown in the dialog
    }
    await refresh();
    onChanged(message);
    if (closeAfter) onClose();
  }

  const e = expense.data;
  const isOwner = !!e && !!user && e.submitted_by_id === user.id;
  const busy = action.isPending;

  function handleReceipt(file: File | undefined) {
    if (!file || !e) return;
    if (!RECEIPT_TYPES.includes(file.type)) return setError('Receipt must be an image (PNG, JPG, WebP) or a PDF');
    if (file.size > MAX_RECEIPT_BYTES) return setError('Receipt must be 10 MB or smaller');
    run(() => expensesApi.uploadReceipt(e.id, file), `Receipt attached to ${e.reference}.`);
  }

  function submitReject(ev: FormEvent) {
    ev.preventDefault();
    if (!e || reason.trim().length < 3) return;
    run(() => expensesApi.reject(e.id, reason.trim()), `${e.reference} rejected.`, true);
  }

  return (
    <dialog
      ref={dialogRef}
      className="modal modal--wide"
      onCancel={(ev) => busy && ev.preventDefault()}
      onClose={onClose}
      aria-labelledby="expense-detail-title"
    >
      <div className="modal-body">
        <div className="modal-head">
          <h2 id="expense-detail-title">
            {e ? <>{e.reference} <span className={`pill pill--${e.status}`}>{e.status}</span></> : 'Expense'}
          </h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close" disabled={busy}>
            <X size={18} />
          </button>
        </div>

        {expense.isPending && open && <p className="empty">Loading…</p>}
        {expense.isError && <Alert type="error">{(expense.error as Error).message}</Alert>}

        {e && !editing && (
          <>
            <div className="detail-hero">
              <div>
                <p className="detail-merchant">{e.merchant}</p>
                <p className="muted">{longDate.format(new Date(`${e.expense_date}T00:00:00`))}</p>
              </div>
              <p className="detail-amount">{formatMoney(e.amount)}</p>
            </div>

            {e.status === 'rejected' && e.rejection_reason && (
              <Alert type="error">Rejected by {e.reviewed_by ?? 'a reviewer'}: {e.rejection_reason}</Alert>
            )}

            <dl className="detail-grid">
              <div><dt>Category</dt><dd>{e.category}</dd></div>
              <div><dt>Department</dt><dd>{e.department}</dd></div>
              <div><dt>Submitted by</dt><dd>{e.submitted_by}</dd></div>
              <div>
                <dt>Submitted</dt>
                <dd>{e.submitted_at ? dateTime.format(new Date(e.submitted_at)) : 'Not yet'}</dd>
              </div>
              {e.reviewed_by && (
                <div>
                  <dt>Reviewed by</dt>
                  <dd>{e.reviewed_by}{e.reviewed_at ? ` · ${dateTime.format(new Date(e.reviewed_at))}` : ''}</dd>
                </div>
              )}
              <div className="detail-wide"><dt>Notes</dt><dd>{e.notes || <span className="muted">None</span>}</dd></div>
              <div className="detail-wide">
                <dt>Receipt</dt>
                <dd className="detail-receipt">
                  {e.has_receipt ? (
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() => expensesApi.openReceipt(e.id).catch((err) => setError(err.message))}
                    >
                      <Paperclip size={14} aria-hidden="true" /> {e.receipt_filename ?? 'Open receipt'}
                    </button>
                  ) : (
                    <span className="status-tag status-tag--warning">No receipt</span>
                  )}
                  {isOwner && e.status !== 'approved' && (
                    <label className="btn btn--ghost btn--sm">
                      <Upload size={14} aria-hidden="true" /> {e.has_receipt ? 'Replace' : 'Upload'}
                      <input
                        type="file"
                        className="sr-only"
                        accept={RECEIPT_TYPES.join(',')}
                        disabled={busy}
                        onChange={(ev) => {
                          handleReceipt(ev.target.files?.[0]);
                          ev.target.value = '';
                        }}
                      />
                    </label>
                  )}
                  {e.has_receipt && e.can_edit && (
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      disabled={busy}
                      onClick={() => run(() => expensesApi.removeReceipt(e.id), `Receipt removed from ${e.reference}.`)}
                    >
                      Remove
                    </button>
                  )}
                </dd>
              </div>
            </dl>

            <section aria-label="History">
              <h3 className="detail-subhead"><Clock size={14} aria-hidden="true" /> History</h3>
              {history.isPending ? (
                <p className="muted">Loading…</p>
              ) : (
                <ol className="timeline">
                  {(history.data ?? []).map((ev, i) => (
                    <li key={i}>
                      <span className={`timeline-dot timeline-dot--${ev.action}`} aria-hidden="true" />
                      <div>
                        <p>
                          <strong>{ACTION_TEXT[ev.action] ?? ev.action}</strong>
                          {ev.actor && <span className="muted"> by {ev.actor}</span>}
                        </p>
                        {ev.comment && <p className="timeline-comment">“{ev.comment}”</p>}
                        <p className="muted timeline-time">{dateTime.format(new Date(ev.created_at))}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            {rejecting && (
              <form onSubmit={submitReject} className="inline-form">
                <label className="sr-only" htmlFor="detail-reason">Reason for rejecting</label>
                <input
                  id="detail-reason"
                  className="field-input"
                  placeholder="Reason (shown to the submitter)"
                  value={reason}
                  maxLength={500}
                  autoFocus
                  onChange={(ev) => setReason(ev.target.value)}
                />
                <Button type="submit" loading={busy} disabled={reason.trim().length < 3}>Reject</Button>
              </form>
            )}

            {confirmDelete && (
              <div className="confirm-row">
                <span>Delete {e.reference} permanently?</span>
                <Button variant="ghost" onClick={() => setConfirmDelete(false)} disabled={busy}>Cancel</Button>
                <Button
                  className="btn--danger"
                  loading={busy}
                  onClick={() => run(() => expensesApi.remove(e.id), `${e.reference} deleted.`, true)}
                >
                  Delete
                </Button>
              </div>
            )}

            {error && <Alert type="error">{error}</Alert>}

            <div className="modal-actions modal-actions--spread">
              <div className="action-group">
                {e.can_edit && (
                  <>
                    <Button variant="ghost" onClick={() => setConfirmDelete(true)} disabled={busy}>
                      <Trash2 size={15} aria-hidden="true" /> Delete
                    </Button>
                    <Button variant="ghost" onClick={() => setEditing(true)} disabled={busy}>
                      <Pencil size={15} aria-hidden="true" /> Edit
                    </Button>
                  </>
                )}
                {isOwner && e.status === 'pending' && (
                  <Button
                    variant="ghost"
                    disabled={busy}
                    onClick={() => run(() => expensesApi.withdraw(e.id), `${e.reference} withdrawn to draft.`)}
                  >
                    <Undo2 size={15} aria-hidden="true" /> Withdraw
                  </Button>
                )}
              </div>
              <div className="action-group">
                {e.can_edit && (
                  <Button
                    loading={busy}
                    onClick={() => run(() => expensesApi.submit(e.id), `${e.reference} submitted for approval.`)}
                  >
                    <Send size={15} aria-hidden="true" /> {e.status === 'rejected' ? 'Resubmit' : 'Submit'}
                  </Button>
                )}
                {e.can_review && (
                  <>
                    <Button variant="ghost" onClick={() => setRejecting((r) => !r)} disabled={busy}>
                      <X size={15} aria-hidden="true" /> Reject
                    </Button>
                    <Button
                      loading={busy && !rejecting}
                      onClick={() => run(() => expensesApi.approve(e.id), `${e.reference} approved.`, true)}
                    >
                      <Check size={15} aria-hidden="true" /> Approve
                    </Button>
                  </>
                )}
              </div>
            </div>
          </>
        )}

        {e && editing && (
          <EditForm
            expense={e}
            onCancel={() => setEditing(false)}
            onSaved={async (updated) => {
              setEditing(false);
              await refresh();
              onChanged(`${updated.reference} updated.`);
            }}
          />
        )}
      </div>
    </dialog>
  );
}

function EditForm({
  expense, onCancel, onSaved,
}: { expense: Expense; onCancel: () => void; onSaved: (e: Expense) => void }) {
  const [error, setError] = useState<string | null>(null);
  const {
    register, handleSubmit, formState: { errors, isSubmitting },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      merchant: expense.merchant,
      amount: expense.amount,
      date: expense.expense_date,
      category: expense.category as ExpenseFormValues['category'],
      department: expense.department as ExpenseFormValues['department'],
      notes: expense.notes ?? '',
    },
  });

  const save = handleSubmit(async (v) => {
    setError(null);
    try {
      const updated = await expensesApi.update(expense.id, {
        merchant: v.merchant,
        amount: v.amount,
        expense_date: v.date,
        category: v.category,
        department: v.department,
        notes: v.notes ?? '',
      });
      onSaved(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  });

  return (
    <form onSubmit={save} noValidate className="modal-form">
      {expense.status === 'rejected' && (
        <p className="muted">Saving changes moves this expense back to draft so you can resubmit it.</p>
      )}
      <Input id="edit-merchant" label="Merchant" error={errors.merchant?.message} {...register('merchant')} />
      <div className="form-row">
        <Input
          id="edit-amount" label="Amount (USD)" type="number" step="0.01" min="0" inputMode="decimal"
          error={errors.amount?.message} {...register('amount', { valueAsNumber: true })}
        />
        <Input
          id="edit-date" label="Date" type="date" max={new Date().toISOString().slice(0, 10)}
          error={errors.date?.message} {...register('date')}
        />
      </div>
      <div className="form-row">
        <div className="field">
          <label className="field-label" htmlFor="edit-category">Category</label>
          <select id="edit-category" className="field-input" {...register('category')}>
            {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="field">
          <label className="field-label" htmlFor="edit-department">Department</label>
          <select id="edit-department" className="field-input" {...register('department')}>
            {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>
      <div className="field">
        <label className="field-label" htmlFor="edit-notes">Notes</label>
        <textarea id="edit-notes" rows={2} className="field-input" {...register('notes')} />
      </div>
      {error && <Alert type="error">{error}</Alert>}
      <div className="modal-actions">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={isSubmitting}>Cancel</Button>
        <Button type="submit" loading={isSubmitting}>Save changes</Button>
      </div>
    </form>
  );
}
