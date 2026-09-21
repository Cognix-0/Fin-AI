'use client';
import React, { InputHTMLAttributes, forwardRef, useState } from 'react';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id, type, className = '', ...props }, ref) => {
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === 'password';
    const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

    return (
      <div className="field">
        <label className="field-label" htmlFor={id}>
          {label}
        </label>
        <div className="field-input-wrap">
          <input
            ref={ref}
            id={id}
            type={inputType}
            className={`field-input ${error ? 'field-input--error' : ''} ${className}`}
            aria-invalid={!!error}
            aria-describedby={error ? `${id}-error` : undefined}
            style={isPassword ? { paddingRight: '3rem' } : {}}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              className="field-input-icon"
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              tabIndex={-1}
            >
              {showPassword
                ? <EyeOff size={17} />
                : <Eye size={17} />}
            </button>
          )}
        </div>
        {error && (
          <p className="field-error" id={`${id}-error`} role="alert">
            <AlertCircle size={13} aria-hidden="true" />
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
