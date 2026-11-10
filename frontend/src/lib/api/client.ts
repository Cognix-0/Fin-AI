const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const API_URL = `${API_BASE}/api/v1`;

export type ApiError = Error & { code: string; status: number };

// Errors that mean "access token is gone or stale" — worth one refresh attempt
const REFRESHABLE = ['TOKEN_EXPIRED', 'NOT_AUTHENTICATED', 'INVALID_TOKEN'];
// Endpoints that must never trigger a refresh-and-retry
const NO_RETRY = ['/auth/login', '/auth/register', '/auth/logout', '/auth/refresh'];

function toError(status: number, data: unknown): ApiError {
  const d = (data ?? {}) as {
    error?: { code?: string; message?: string };
    detail?: { code?: string; message?: string } | string;
  };
  const detail = typeof d.detail === 'object' ? d.detail : undefined;
  const message =
    d.error?.message ??
    detail?.message ??
    (typeof d.detail === 'string' ? d.detail : undefined) ??
    'Something went wrong';
  const err = new Error(message) as ApiError;
  err.code = d.error?.code ?? detail?.code ?? 'UNKNOWN_ERROR';
  err.status = status;
  return err;
}

// One shared in-flight refresh so parallel 401s don't each rotate the token
// (rotating twice would trip the backend's reuse detection).
let refreshing: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(`${API_URL}/auth/refresh`, { method: 'POST', credentials: 'include' })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export function buildQuery(params: Record<string, string | number | boolean | undefined | null>) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : '';
}

/** Low-level request that retries once after refreshing the session. Returns the raw Response. */
export async function apiRequest(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const isForm = options.body instanceof FormData;
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include', // send/receive cookies
    headers: {
      ...(isForm || options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  });

  if (res.status === 401 && retry && !NO_RETRY.includes(path)) {
    const data = await res.clone().json().catch(() => null);
    if (REFRESHABLE.includes(toError(401, data).code) && (await refreshSession())) {
      return apiRequest(path, options, false);
    }
  }
  return res;
}

/** JSON request helper: throws an ApiError carrying the backend's code and message. */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiRequest(path, options);
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw toError(res.status, data);
  return data as T;
}

/** Fetch a file (CSV export, receipt) and hand it to the browser as a download or new tab. */
export async function apiDownload(path: string, fallbackName: string, open = false) {
  const res = await apiRequest(path);
  if (!res.ok) throw toError(res.status, await res.json().catch(() => null));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  if (open) {
    window.open(url, '_blank', 'noopener');
  } else {
    const disposition = res.headers.get('Content-Disposition') ?? '';
    const name = /filename="?([^"]+)"?/.exec(disposition)?.[1] ?? fallbackName;
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
