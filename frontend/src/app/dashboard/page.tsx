import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Dashboard — FinanceOS',
};

// This page is protected by middleware.ts
export default function DashboardPage() {
  return (
    <main style={{
      minHeight: '100dvh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '1.5rem',
      padding: '2rem',
    }}>
      <div style={{ textAlign: 'center', maxWidth: '480px' }}>
        <div className="logo" style={{ justifyContent: 'center', marginBottom: '2rem' }}>
          <div className="logo-mark">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 13 L7 8 L10 11 L15 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="logo-text">FinanceOS</span>
        </div>

        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '0.75rem' }}>
          You're in.
        </h1>
        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '2rem', lineHeight: 1.6 }}>
          Welcome to FinanceOS. Your dashboard is being set up in Phase 2.
          For now, you've successfully authenticated.
        </p>

        <div style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: '1.25rem 1.5rem',
          marginBottom: '1.5rem',
          textAlign: 'left',
        }}>
          <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
            Auth status
          </p>
          <p style={{ fontSize: '0.9375rem', color: 'var(--color-success)', fontWeight: 500 }}>
            ✓ Authenticated via JWT cookie
          </p>
        </div>

        <form action="/api/logout" method="POST">
          <Link
            href="/login"
            className="btn btn--ghost"
            style={{ fontSize: '0.875rem' }}
          >
            Sign out
          </Link>
        </form>
      </div>
    </main>
  );
}
