import { z } from 'zod';
import { EXPENSE_CATEGORIES } from '@/lib/mock/dashboard';

export const DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'Operations'] as const;

export const expenseSchema = z.object({
  merchant: z
    .string()
    .trim()
    .min(2, 'Merchant must be at least 2 characters')
    .max(120, 'Merchant name is too long'),
  amount: z
    .number({ error: 'Enter an amount' })
    .positive('Amount must be greater than 0')
    .max(1_000_000, 'Amount is too large'),
  date: z
    .string()
    .min(1, 'Date is required')
    .refine((d) => new Date(d) <= new Date(), 'Date cannot be in the future'),
  category: z.enum(EXPENSE_CATEGORIES as [string, ...string[]], { error: 'Pick a category' }),
  department: z.enum(DEPARTMENTS, { error: 'Pick a department' }),
  notes: z.string().max(500, 'Notes are too long').optional(),
});

export type ExpenseFormValues = z.infer<typeof expenseSchema>;
