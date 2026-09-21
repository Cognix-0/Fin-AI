import type { Metadata } from 'next';
import { AuthPanel } from '@/components/auth/AuthPanel';
import { LoginForm } from '@/components/auth/LoginForm';

export const metadata: Metadata = {
  title: 'Sign in — FinanceOS',
  description: 'Sign in to your FinanceOS account to manage company expenses.',
};

export default function LoginPage() {
  return (
    <main className="auth-layout">
      <AuthPanel />
      <div className="auth-panel-form animate-fade-in">
        <LoginForm />
      </div>
    </main>
  );
}
