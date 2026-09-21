'use client';
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { registerSchema, RegisterFormValues } from '@/lib/validation/auth';
import { authApi } from '@/lib/api/auth';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

export function RegisterForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (values: RegisterFormValues) => {
    setServerError(null);
    try {
      await authApi.register(values);
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
      style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}
    >
      {/* Header */}
      <div style={{ marginBottom: '0.25rem' }}>
        <div className="logo" style={{ marginBottom: '2rem' }}>
          <div className="logo-mark">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 13 L7 8 L10 11 L15 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="logo-text">FinanceOS</span>
        </div>
        <h1 style={{ fontSize: '1.625rem', fontWeight: 600, marginBottom: '0.375rem', lineHeight: 1.2 }}>
          Create your account
        </h1>
        <p style={{ fontSize: '0.9375rem', color: 'var(--color-text-secondary)' }}>
          Start managing your team's expenses today
        </p>
      </div>

      {/* Server error */}
      {serverError && <Alert type="error">{serverError}</Alert>}
      {success && <Alert type="success">Account created — taking you to your dashboard…</Alert>}

      {/* Fields */}
      <Input
        id="reg-name"
        label="Full name"
        type="text"
        placeholder="Jane Smith"
        autoComplete="name"
        error={errors.full_name?.message}
        {...register('full_name')}
      />

      <Input
        id="reg-email"
        label="Work email"
        type="email"
        placeholder="you@company.com"
        autoComplete="email"
        error={errors.email?.message}
        {...register('email')}
      />

      <Input
        id="reg-password"
        label="Password"
        type="password"
        placeholder="8+ characters, one uppercase, one number"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register('password')}
      />

      <Input
        id="reg-confirm-password"
        label="Confirm password"
        type="password"
        placeholder="Same as above"
        autoComplete="new-password"
        error={errors.confirm_password?.message}
        {...register('confirm_password')}
      />

      {/* Role notice */}
      <p style={{
        fontSize: '0.8125rem',
        color: 'var(--color-text-muted)',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.625rem 0.875rem',
        lineHeight: 1.5,
      }}>
        New accounts start with <strong style={{ color: 'var(--color-text-secondary)' }}>Employee</strong> access.
        Your admin can update your role.
      </p>

      <Button
        type="submit"
        fullWidth
        loading={isSubmitting}
        disabled={isSubmitting}
        id="register-submit"
      >
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </Button>

      <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
        Already have an account?{' '}
        <Link
          href="/login"
          style={{ color: 'var(--color-accent)', textDecoration: 'none', fontWeight: 500 }}
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
