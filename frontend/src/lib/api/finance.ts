import {
  AnalyticsSummary, Budget, BudgetCopyResult, BulkDecisionResult, Expense, ExpenseEvent,
  ExpenseInput, ExpenseQuery, ExpenseUpdate, Page, Period,
} from '@/types/finance';
import { apiDownload, apiFetch, buildQuery } from './client';

type Envelope<T> = { success: boolean; data: T };
type ExpenseEnvelope = Envelope<{ expense: Expense }>;

const post = (path: string, body?: unknown) =>
  apiFetch<ExpenseEnvelope>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then((r) => r.data.expense);

export const expensesApi = {
  list: (q: ExpenseQuery = {}) =>
    apiFetch<Envelope<Page<Expense>>>(`/expenses${buildQuery({ ...q })}`).then((r) => r.data),

  get: (id: number) =>
    apiFetch<ExpenseEnvelope>(`/expenses/${id}`).then((r) => r.data.expense),

  history: (id: number) =>
    apiFetch<Envelope<{ events: ExpenseEvent[] }>>(`/expenses/${id}/history`).then((r) => r.data.events),

  create: (body: ExpenseInput) => post('/expenses', body),

  update: (id: number, body: ExpenseUpdate) =>
    apiFetch<ExpenseEnvelope>(`/expenses/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }).then((r) => r.data.expense),

  remove: (id: number) => apiFetch<void>(`/expenses/${id}`, { method: 'DELETE' }),

  submit: (id: number) => post(`/expenses/${id}/submit`),
  withdraw: (id: number) => post(`/expenses/${id}/withdraw`),
  approve: (id: number, comment?: string) => post(`/expenses/${id}/approve`, { comment }),
  reject: (id: number, reason: string) => post(`/expenses/${id}/reject`, { reason }),

  bulkDecision: (ids: number[], action: 'approve' | 'reject', reason?: string) =>
    apiFetch<Envelope<BulkDecisionResult>>('/expenses/bulk-decision', {
      method: 'POST',
      body: JSON.stringify({ ids, action, reason }),
    }).then((r) => r.data),

  uploadReceipt: (id: number, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<ExpenseEnvelope>(`/expenses/${id}/receipt`, {
      method: 'POST',
      body: form,
    }).then((r) => r.data.expense);
  },

  removeReceipt: (id: number) =>
    apiFetch<ExpenseEnvelope>(`/expenses/${id}/receipt`, { method: 'DELETE' }).then((r) => r.data.expense),

  openReceipt: (id: number) => apiDownload(`/expenses/${id}/receipt`, 'receipt', true),

  // Paging doesn't apply to exports: the backend returns every matching row (max 10k)
  exportCsv: (q: ExpenseQuery = {}) =>
    apiDownload(
      `/expenses/export${buildQuery({ ...q, page: undefined, page_size: undefined })}`,
      'expenses.csv',
    ),
};

export const budgetsApi = {
  /** `month` is any YYYY-MM-DD in the month; `all` also returns departments with no budget. */
  list: (month?: string, all = false) =>
    apiFetch<Envelope<{ items: Budget[] }>>(`/budgets${buildQuery({ month, include_unbudgeted: all })}`)
      .then((r) => r.data.items),

  upsert: (department: string, month: string, amount_limit: number) =>
    apiFetch<Envelope<{ budget: Budget }>>('/budgets', {
      method: 'PUT',
      body: JSON.stringify({ department, month, amount_limit }),
    }).then((r) => r.data.budget),

  copy: (from_month: string, to_month: string, overwrite = false) =>
    apiFetch<Envelope<BudgetCopyResult>>('/budgets/copy', {
      method: 'POST',
      body: JSON.stringify({ from_month, to_month, overwrite }),
    }).then((r) => r.data),

  remove: (id: number) => apiFetch<void>(`/budgets/${id}`, { method: 'DELETE' }),
};

export const analyticsApi = {
  summary: (period: Period) =>
    apiFetch<Envelope<AnalyticsSummary>>(`/analytics/summary${buildQuery({ period })}`).then((r) => r.data),
};
