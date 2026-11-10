// Shapes returned by the finance API (backend/app/schemas/*).

export type ExpenseStatus = 'draft' | 'pending' | 'approved' | 'rejected';

export interface Expense {
  id: number;
  reference: string;          // "EXP-1042"
  merchant: string;
  amount: number;
  currency: string;
  expense_date: string;       // YYYY-MM-DD
  category: string;
  department: string;
  notes: string | null;
  status: ExpenseStatus;
  submitted_by: string;
  submitted_by_id: string;
  submitted_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  has_receipt: boolean;
  receipt_filename: string | null;
  created_at: string;
  updated_at: string;
  can_edit: boolean;          // what the *current user* may do
  can_review: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type ExpenseSort = '-date' | 'date' | '-amount' | 'amount' | '-created';

export interface ExpenseQuery {
  status?: ExpenseStatus;
  category?: string;
  department?: string;
  search?: string;
  mine?: boolean;
  missing_receipt?: boolean;
  date_from?: string;         // YYYY-MM-DD
  date_to?: string;
  min_amount?: number;
  max_amount?: number;
  page?: number;
  page_size?: number;
  sort?: ExpenseSort;
}

export interface ExpenseInput {
  merchant: string;
  amount: number;
  expense_date: string;
  category: string;
  department: string;
  notes?: string;
  submit?: boolean;
}

export type ExpenseUpdate = Partial<Omit<ExpenseInput, 'submit'>>;

export interface ExpenseEvent {
  action: string;             // created | updated | submitted | withdrawn | approved | rejected | receipt_added | receipt_replaced | receipt_removed
  from_status: string | null;
  to_status: string | null;
  comment: string | null;
  actor: string | null;
  created_at: string;
}

export interface BudgetCopyResult {
  created: number;
  updated: number;
  skipped: number;
}

export type BudgetStatus = 'on_track' | 'near_limit' | 'over_budget' | 'no_budget';

export interface Budget {
  id: number | null;
  department: string;
  month: string;
  limit: number;
  spent: number;              // approved
  pending: number;            // awaiting approval
  remaining: number;
  utilization: number;        // (spent + pending) / limit * 100
  status: BudgetStatus;
}

export type Period = '30d' | 'quarter' | 'year';

export interface MonthlySpend {
  month: string;              // YYYY-MM
  label: string;              // "Oct"
  amount: number;
}

export interface Insight {
  tone: 'warning' | 'info';
  kind: string;
  text: string;
  expense_id?: number;
}

export interface AnalyticsSummary {
  period: Period;
  scope: 'company' | 'department' | 'personal';
  range: { start: string; end: string };
  kpis: {
    total_spend: number;
    previous_spend: number;
    change_pct: number | null;
    expense_count: number;
    average_expense: number;
    pending_count: number;
    pending_total: number;
    missing_receipts: number;
    budget_limit: number;
    budget_committed: number;
    budget_utilization: number | null;
  };
  monthly: MonthlySpend[];
  by_category: { category: string; amount: number; share: number }[];
  by_department: { department: string; amount: number }[];
  top_merchants: { merchant: string; amount: number; count: number }[];
  insights: Insight[];
}

export interface BulkDecisionResult {
  succeeded: number[];
  failed: { id: number; code: string; message: string }[];
}
