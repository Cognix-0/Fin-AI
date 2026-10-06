'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api/auth';
import { Button } from '@/components/ui/Button';

export function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSignOut() {
    setLoading(true);
    try {
      // Backend clears the HTTP-only cookie; middleware then allows /login
      await authApi.logout();
    } finally {
      router.replace('/login');
      router.refresh();
    }
  }

  return (
    <Button
      variant="ghost"
      loading={loading}
      onClick={handleSignOut}
      style={{ fontSize: '0.875rem' }}
    >
      Sign out
    </Button>
  );
}
