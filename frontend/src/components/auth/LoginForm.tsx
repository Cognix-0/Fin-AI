'use client';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { loginSchema, LoginFormValues } from '@/lib/validation/auth';
import { authApi } from '@/lib/api/auth';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

export function LoginForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (values: LoginFormValues) => {
    setServerError(null);
    try {
      await authApi.login(values);
      setSuccess(true);
      router.push('/dashboard');
      router.refresh();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Something went wrong';
      setServerError(message);
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
    >
      {/* Header */}
      <div style={{ marginBottom: '0.5rem' }}>
        <div className="logo" style={{ marginBottom: '2rem' }}>
          <div className="logo-mark">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 13 L7 8 L10 11 L15 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="logo-text">FinanceOS</span>
        </div>
        <h1 style={{ fontSize: '1.625rem', fontWeight: 600, marginBottom: '0.375rem', lineHeight: 1.2 }}>
          Sign in to your account
        </h1>
        <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-secondary)' }}>
          Enter your credentials to continue
        </p>
      </div>

      {/* Server error */}
      {serverError && <Alert type="error">{serverError}</Alert>}
      {success && <Alert type="success">Signing you in…</Alert>}

      {/* Fields */}
      <Input
        id="login-email"
        label="Email address"
        type="email"
        placeholder="you@company.com"
        autoComplete="email"
        error={errors.email?.message}
        {...register('email')}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <Input
          id="login-password"
          label="Password"
          type="password"
          placeholder="Your password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <Link
          href="/forgot-password"
          style={{
            alignSelf: 'flex-end',
            fontSize: '0.8125rem',
            color: 'var(--color-accent)',
            textDecoration: 'none',
          }}
        >
          Forgot password?
        </Link>
      </div>

      <Button
        type="submit"
        fullWidth
        loading={isSubmitting}
        disabled={isSubmitting}
        id="login-submit"
      >
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </Button>

      <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        No account?{' '}
        <Link
          href="/register"
          style={{ color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 500 }}
        >
          Create one
        </Link>
      </p>
    </form>
  );
}
