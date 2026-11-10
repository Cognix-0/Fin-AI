import { ExpenseStatus, Period } from '@/types/finance';

// Must match the rows seeded by backend migration 002_finance_core
// (also served at GET /api/v1/meta).
export const EXPENSE_CATEGORIES = [
  'Travel', 'Software', 'Meals', 'Office', 'Marketing', 'Utilities',
] as const;

export const DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'Operations'] as const;

export const EXPENSE_STATUSES: ExpenseStatus[] = ['pending', 'approved', 'rejected', 'draft'];

export const PERIODS: { value: Period; label: string; months: number }[] = [
  { value: '30d', label: 'Last 30 days', months: 1 },
  { value: 'quarter', label: 'Quarter', months: 3 },
  { value: 'year', label: '12 months', months: 12 },
];
