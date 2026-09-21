import type { Metadata } from 'next';
import { AuthPanel } from '@/components/auth/AuthPanel';
import { RegisterForm } from '@/components/auth/RegisterForm';

export const metadata: Metadata = {
  title: 'Create account — FinanceOS',
  description: 'Create your FinanceOS account to start managing company expenses.',
};

export default function RegisterPage() {
  return (
    <main className="auth-layout">
      <AuthPanel />
      <div className="auth-panel-form animate-fade-in">
        <RegisterForm />
      </div>
    </main>
  );
}
