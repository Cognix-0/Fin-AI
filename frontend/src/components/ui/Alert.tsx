import React, { ReactNode } from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface AlertProps {
  type: 'error' | 'success';
  children: ReactNode;
}

export function Alert({ type, children }: AlertProps) {
  const Icon = type === 'error' ? AlertCircle : CheckCircle2;
  return (
    <div className={`alert alert--${type}`} role="alert">
      <Icon size={16} aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }} />
      <span>{children}</span>
    </div>
  );
}
