'use client';
import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api/auth';
import { User } from '@/types/auth';

const SESSION_ERRORS = ['NOT_AUTHENTICATED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'];

interface CurrentUserState {
  user: User | null;
  loading: boolean;
}

const CurrentUserContext = createContext<CurrentUserState>({ user: null, loading: true });

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<CurrentUserState>({ user: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    authApi
      .me()
      .then((res) => {
        if (!cancelled) setState({ user: res.data.user, loading: false });
      })
      .catch(async (err: Error & { code?: string }) => {
        if (cancelled) return;
        // Cookie present but rejected: clear it so middleware stops treating
        // us as signed in, then send the user back to /login.
        if (SESSION_ERRORS.includes(err.code ?? '')) {
          await authApi.logout().catch(() => {});
          router.replace('/login');
          router.refresh();
          return;
        }
        setState({ user: null, loading: false });
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  return <CurrentUserContext.Provider value={state}>{children}</CurrentUserContext.Provider>;
}

export function useCurrentUser() {
  return useContext(CurrentUserContext);
}

const APPROVER_ROLES = ['MANAGER', 'FINANCE_ADMIN', 'SYSTEM_ADMIN'];

export function canApprove(user: User | null) {
  return Boolean(user?.roles.some((r) => APPROVER_ROLES.includes(r)));
}

export function formatRole(role: string) {
  return role
    .toLowerCase()
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}
