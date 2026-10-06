// Sample data for the dashboard UI.
// The backend currently exposes auth endpoints only — replace these with
// API calls once the expense / budget endpoints exist (frontend-roadmap Phase 6–7).

export type ExpenseStatus = 'draft' | 'pending' | 'approved' | 'rejected';

export type ExpenseCategory =
  | 'Travel'
  | 'Software'
  | 'Meals'
  | 'Office'
  | 'Marketing'
  | 'Utilities';

export const EXPENSE_CATEGORIES: ExpenseCategory[] = [
  'Travel', 'Software', 'Meals', 'Office', 'Marketing', 'Utilities',
];

export interface Expense {
  id: string;
  date: string;          // ISO date (YYYY-MM-DD)
  merchant: string;
  category: ExpenseCategory;
  department: string;
  submittedBy: string;
  amount: number;
  status: ExpenseStatus;
  hasReceipt: boolean;
}

export interface MonthlySpend {
  month: string;         // short label, e.g. "Oct"
  amount: number;
}

export interface Budget {
  department: string;
  spent: number;
  limit: number;
}

export type Period = '30d' | 'quarter' | 'year';

export const PERIODS: { value: Period; label: string; months: number }[] = [
  { value: '30d', label: 'Last 30 days', months: 1 },
  { value: 'quarter', label: 'Quarter', months: 3 },
  { value: 'year', label: '12 months', months: 12 },
];

export const monthlySpend: MonthlySpend[] = [
  { month: 'Oct', amount: 38200 },
  { month: 'Nov', amount: 41750 },
  { month: 'Dec', amount: 52300 },
  { month: 'Jan', amount: 36900 },
  { month: 'Feb', amount: 39400 },
  { month: 'Mar', amount: 44100 },
  { month: 'Apr', amount: 42800 },
  { month: 'May', amount: 47650 },
  { month: 'Jun', amount: 45200 },
  { month: 'Jul', amount: 49800 },
  { month: 'Aug', amount: 46300 },
  { month: 'Sep', amount: 51900 },
];

export const budgets: Budget[] = [
  { department: 'Engineering', spent: 18400, limit: 24000 },
  { department: 'Sales', spent: 14950, limit: 16000 },
  { department: 'Marketing', spent: 12800, limit: 12000 },
  { department: 'Operations', spent: 5750, limit: 10000 },
];

export const initialExpenses: Expense[] = [
  { id: 'EXP-1042', date: '2026-09-22', merchant: 'Delta Air Lines', category: 'Travel', department: 'Sales', submittedBy: 'Priya Nair', amount: 1248.4, status: 'pending', hasReceipt: true },
  { id: 'EXP-1041', date: '2026-09-21', merchant: 'Figma', category: 'Software', department: 'Engineering', submittedBy: 'Kasun Perera', amount: 540, status: 'pending', hasReceipt: true },
  { id: 'EXP-1040', date: '2026-09-20', merchant: 'Hilton Colombo', category: 'Travel', department: 'Sales', submittedBy: 'Priya Nair', amount: 812.75, status: 'approved', hasReceipt: true },
  { id: 'EXP-1039', date: '2026-09-19', merchant: 'Google Ads', category: 'Marketing', department: 'Marketing', submittedBy: 'Amal Silva', amount: 3200, status: 'pending', hasReceipt: false },
  { id: 'EXP-1038', date: '2026-09-18', merchant: 'Staples', category: 'Office', department: 'Operations', submittedBy: 'Nimali Fernando', amount: 186.2, status: 'approved', hasReceipt: true },
  { id: 'EXP-1037', date: '2026-09-17', merchant: 'Ministry of Crab', category: 'Meals', department: 'Sales', submittedBy: 'Ruwan Jayasuriya', amount: 264.5, status: 'rejected', hasReceipt: true },
  { id: 'EXP-1036', date: '2026-09-16', merchant: 'AWS', category: 'Software', department: 'Engineering', submittedBy: 'Kasun Perera', amount: 4870.12, status: 'approved', hasReceipt: true },
  { id: 'EXP-1035', date: '2026-09-15', merchant: 'Dialog Axiata', category: 'Utilities', department: 'Operations', submittedBy: 'Nimali Fernando', amount: 142, status: 'approved', hasReceipt: true },
  { id: 'EXP-1034', date: '2026-09-14', merchant: 'Uber', category: 'Travel', department: 'Engineering', submittedBy: 'Dinuka Rajapaksa', amount: 38.9, status: 'draft', hasReceipt: false },
  { id: 'EXP-1033', date: '2026-09-12', merchant: 'LinkedIn Ads', category: 'Marketing', department: 'Marketing', submittedBy: 'Amal Silva', amount: 1850, status: 'approved', hasReceipt: true },
  { id: 'EXP-1032', date: '2026-09-10', merchant: 'Slack', category: 'Software', department: 'Operations', submittedBy: 'Nimali Fernando', amount: 412.5, status: 'approved', hasReceipt: true },
  { id: 'EXP-1031', date: '2026-09-08', merchant: 'Café Kumbuk', category: 'Meals', department: 'Engineering', submittedBy: 'Dinuka Rajapaksa', amount: 72.3, status: 'pending', hasReceipt: true },
];

export const aiInsights: { tone: 'warning' | 'info'; text: string }[] = [
  { tone: 'warning', text: 'Marketing is 6.7% over its monthly budget, driven by a $3,200 Google Ads charge awaiting approval.' },
  { tone: 'warning', text: 'EXP-1039 has no receipt attached — ask the submitter to upload one before approval.' },
  { tone: 'info', text: 'Software spend is up 18% vs. last month. AWS accounts for 83% of the increase.' },
];
