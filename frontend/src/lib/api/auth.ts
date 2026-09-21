import { LoginRequest, RegisterRequest, AuthResponse, User } from '@/types/auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_URL = `${API_BASE}/api/v1`;

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',   // send/receive cookies
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  const data = await res.json();

  if (!res.ok) {
    // Throw the error detail from the API for the form to display
    const message =
      data?.detail?.message ??
      data?.error?.message ??
      data?.detail ??
      'Something went wrong';
    const code =
      data?.detail?.code ??
      data?.error?.code ??
      'UNKNOWN_ERROR';
    const err = new Error(message) as Error & { code: string };
    err.code = code;
    throw err;
  }

  return data as T;
}

export const authApi = {
  login: (body: LoginRequest) =>
    apiFetch<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  register: (body: RegisterRequest) =>
    apiFetch<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  logout: () =>
    apiFetch<{ success: boolean }>('/auth/logout', { method: 'POST' }),

  me: () =>
    apiFetch<{ success: boolean; data: { user: User } }>('/auth/me'),
};
