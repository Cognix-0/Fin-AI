'use client';
import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Upload, X } from 'lucide-react';

import { DEPARTMENTS, EXPENSE_CATEGORIES } from '@/lib/constants/finance';
import { ExpenseFormValues, expenseSchema } from '@/lib/validation/expense';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

const MAX_RECEIPT_BYTES = 10 * 1024 * 1024;
const RECEIPT_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'application/pdf'];

interface Props {
  open: boolean;
  onClose: () => void;
  /** Resolves when saved; rejects with an Error whose message is shown in the form. */
  onSubmit: (values: ExpenseFormValues, receipt: File | null, asDraft: boolean) => Promise<void>;
  defaultDepartment?: string | null;
}

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p className="field-error" id={id} role="alert">
      <AlertCircle size={13} aria-hidden="true" />
      {message}
    </p>
  );
}

export function NewExpenseModal({ open, onClose, onSubmit, defaultDepartment }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [receipt, setReceipt] = useState<File | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saving, setSaving] = useState<'draft' | 'submit' | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: { date: new Date().toISOString().slice(0, 10) },
  });

  // Native <dialog> gives us focus trapping, Esc-to-close and a backdrop for free
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // Pre-select the user's own department once we know it
  useEffect(() => {
    if (open && defaultDepartment && (DEPARTMENTS as readonly string[]).includes(defaultDepartment)) {
      setValue('department', defaultDepartment as ExpenseFormValues['department']);
    }
  }, [open, defaultDepartment, setValue]);

  function close() {
    if (saving) return;
    reset();
    setReceipt(null);
    setReceiptError(null);
    setSubmitError(null);
    onClose();
  }

  function handleFile(file: File | undefined) {
    setReceiptError(null);
    if (!file) return setReceipt(null);
    if (!RECEIPT_TYPES.includes(file.type)) {
      setReceipt(null);
      return setReceiptError('Receipt must be an image (PNG, JPG, WebP) or a PDF');
    }
    if (file.size > MAX_RECEIPT_BYTES) {
      setReceipt(null);
      return setReceiptError('Receipt must be 10 MB or smaller');
    }
    setReceipt(file);
  }

  const submit = (asDraft: boolean) =>
    handleSubmit(async (values) => {
      setSubmitError(null);
      setSaving(asDraft ? 'draft' : 'submit');
      try {
        await onSubmit(values, receipt, asDraft);
        setSaving(null);
        reset();
        setReceipt(null);
        onClose();
      } catch (e) {
        setSaving(null);
        setSubmitError((e as Error).message);
      }
    });

  return (
    <dialog
      ref={dialogRef}
      className="modal"
      onCancel={(e) => saving && e.preventDefault()}   // don't let Esc close mid-save
      onClose={close}
      aria-labelledby="new-expense-title"
    >
      <form onSubmit={submit(false)} noValidate className="modal-body">
        <div className="modal-head">
          <h2 id="new-expense-title">New expense</h2>
          <button type="button" className="icon-btn" onClick={close} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <Input
          id="merchant"
          label="Merchant"
          placeholder="e.g. Delta Air Lines"
          error={errors.merchant?.message}
          {...register('merchant')}
        />

        <div className="form-row">
          <Input
            id="amount"
            label="Amount (USD)"
            type="number"
            step="0.01"
            min="0"
            inputMode="decimal"
            placeholder="0.00"
            error={errors.amount?.message}
            {...register('amount', { valueAsNumber: true })}
          />
          <Input
            id="date"
            label="Date"
            type="date"
            max={new Date().toISOString().slice(0, 10)}
            error={errors.date?.message}
            {...register('date')}
          />
        </div>

        <div className="form-row">
          <div className="field">
            <label className="field-label" htmlFor="category">Category</label>
            <select
              id="category"
              className={`field-input ${errors.category ? 'field-input--error' : ''}`}
              aria-invalid={!!errors.category}
              defaultValue=""
              {...register('category')}
            >
              <option value="" disabled>Select…</option>
              {EXPENSE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <FieldError id="category-error" message={errors.category?.message} />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="department">Department</label>
            <select
              id="department"
              className={`field-input ${errors.department ? 'field-input--error' : ''}`}
              aria-invalid={!!errors.department}
              defaultValue=""
              {...register('department')}
            >
              <option value="" disabled>Select…</option>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <FieldError id="department-error" message={errors.department?.message} />
          </div>
        </div>

        <div className="field">
          <span className="field-label">Receipt</span>
          <label className="dropzone">
            <Upload size={18} aria-hidden="true" />
            <span>{receipt ? receipt.name : 'Upload image or PDF (max 10 MB)'}</span>
            <input
              type="file"
              accept={RECEIPT_TYPES.join(',')}
              className="sr-only"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>
          <FieldError id="receipt-error" message={receiptError ?? undefined} />
        </div>

        <div className="field">
          <label className="field-label" htmlFor="notes">Notes (optional)</label>
          <textarea
            id="notes"
            rows={2}
            className="field-input"
            placeholder="Business purpose, attendees…"
            {...register('notes')}
          />
          <FieldError id="notes-error" message={errors.notes?.message} />
        </div>

        {submitError && <Alert type="error">{submitError}</Alert>}

        <div className="modal-actions">
          <Button type="button" variant="ghost" onClick={submit(true)} loading={saving === 'draft'} disabled={!!saving}>
            Save draft
          </Button>
          <Button type="submit" loading={saving === 'submit'} disabled={!!saving}>
            Submit for approval
          </Button>
        </div>
      </form>
    </dialog>
  );
}
