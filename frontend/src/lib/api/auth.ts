import { LoginRequest, RegisterRequest, AuthResponse, User } from '@/types/auth';
import { apiFetch } from './client';

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

  refresh: () =>
    apiFetch<{ success: boolean; data: { user: User } }>('/auth/refresh', { method: 'POST' }),

  me: () =>
    apiFetch<{ success: boolean; data: { user: User } }>('/auth/me'),
};
