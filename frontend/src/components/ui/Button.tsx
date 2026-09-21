'use client';
import React, { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost';
  fullWidth?: boolean;
  loading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  fullWidth = false,
  loading = false,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const classes = [
    'btn',
    `btn--${variant}`,
    fullWidth ? 'btn--full' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      {...props}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
