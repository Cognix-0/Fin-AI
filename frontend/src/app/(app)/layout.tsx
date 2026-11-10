import { AppShell } from '@/components/layout/AppShell';

// Shared shell (sidebar + top bar) for every signed-in page.
// Access is enforced by proxy.ts.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
