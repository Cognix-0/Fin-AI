'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Alert } from '@/components/ui/Alert';
import { expensesApi } from '@/lib/api/finance';
import { ExpenseFormValues } from '@/lib/validation/expense';

type ToastState = { type: 'success' | 'error'; text: string } | null;

/** Small transient status message, shown bottom-right. */
export function useToast() {
  const [toast, setToast] = useState<ToastState>(null);
  const timer = useRef<number | undefined>(undefined);

  const flash = useCallback((text: string, type: 'success' | 'error' = 'success') => {
    window.clearTimeout(timer.current);
    setToast({ type, text });
    timer.current = window.setTimeout(() => setToast(null), 4500);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const node = toast ? (
    <div className="toast" role="status">
      <Alert type={toast.type}>{toast.text}</Alert>
    </div>
  ) : null;

  return { flash, toastNode: node };
}

/**
 * Create an expense (optionally submitting it) and attach a receipt.
 * Validation/API errors on create propagate so the form can show them;
 * a failed receipt upload is reported via `flash` since the expense itself was saved.
 */
export function useAddExpense(flash: (text: string, type?: 'success' | 'error') => void) {
  const refresh = useRefreshFinance();
  return useCallback(
    async (values: ExpenseFormValues, receipt: File | null, asDraft: boolean) => {
      const created = await expensesApi.create({
        merchant: values.merchant,
        amount: values.amount,
        expense_date: values.date,
        category: values.category,
        department: values.department,
        notes: values.notes || undefined,
        submit: !asDraft,
      });
      let receiptFailed: string | null = null;
      if (receipt) {
        try {
          await expensesApi.uploadReceipt(created.id, receipt);
        } catch (e) {
          receiptFailed = (e as Error).message;
        }
      }
      await refresh();
      if (receiptFailed) {
        flash(`${created.reference} saved, but the receipt upload failed: ${receiptFailed}`, 'error');
      } else {
        flash(asDraft ? `${created.reference} saved as draft.` : `${created.reference} submitted for approval.`);
      }
    },
    [flash, refresh],
  );
}

/** Everything derived from expenses (lists, KPIs, budgets) needs a refetch after a change. */
export function useRefreshFinance() {
  const queryClient = useQueryClient();
  return useCallback(
    () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ['expenses'] }),
        queryClient.invalidateQueries({ queryKey: ['expense'] }),
        queryClient.invalidateQueries({ queryKey: ['analytics'] }),
        queryClient.invalidateQueries({ queryKey: ['budgets'] }),
      ]),
    [queryClient],
  );
}
