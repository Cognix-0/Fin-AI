import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'FinanceOS — AI-Powered Company Finance Management',
  description: 'Manage company expenses, receipts, budgets, and approvals with AI-powered insights.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
