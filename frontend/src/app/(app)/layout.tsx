import { AppShell } from '@/components/layout/AppShell';

// Shared shell (sidebar + top bar) for every signed-in page.
// Access is enforced by middleware.ts.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
