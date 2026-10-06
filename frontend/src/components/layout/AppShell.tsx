'use client';
import { ReactNode, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ChartColumn, ChevronDown, CircleUser, LayoutDashboard, Menu,
  Receipt, Settings, Sparkles, Users, Wallet, CircleCheck, X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { SignOutButton } from '@/components/auth/SignOutButton';
import { CurrentUserProvider, formatRole, useCurrentUser } from '@/hooks/useCurrentUser';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  ready: boolean;       // false = route not built yet (shown as "Soon")
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Overview',
    items: [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, ready: true },
      { label: 'AI Insights', href: '/insights', icon: Sparkles, ready: false },
    ],
  },
  {
    title: 'Finance',
    items: [
      { label: 'Expenses', href: '/expenses', icon: Receipt, ready: false },
      { label: 'Approvals', href: '/approvals', icon: CircleCheck, ready: false },
      { label: 'Budgets', href: '/budgets', icon: Wallet, ready: false },
      { label: 'Reports', href: '/reports', icon: ChartColumn, ready: false },
    ],
  },
  {
    title: 'Organization',
    items: [
      { label: 'Team', href: '/team', icon: Users, ready: false },
      { label: 'Settings', href: '/settings', icon: Settings, ready: false },
    ],
  },
];

function Logo() {
  return (
    <div className="logo">
      <div className="logo-mark">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M3 13 L7 8 L10 11 L15 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <span className="logo-text">FinanceOS</span>
    </div>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      <div
        className={`sidebar-scrim ${open ? 'is-open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar ${open ? 'is-open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-head">
          <Logo />
          <button className="icon-btn sidebar-close" onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="nav-section">
              <p className="nav-section-title">{section.title}</p>
              {section.items.map(({ label, href, icon: Icon, ready }) => {
                const active = pathname === href || pathname.startsWith(`${href}/`);
                if (!ready) {
                  return (
                    <span
                      key={href}
                      className="nav-link is-disabled"
                      aria-disabled="true"
                      title="Coming in a later phase"
                    >
                      <Icon size={17} aria-hidden="true" />
                      {label}
                      <span className="nav-badge">Soon</span>
                    </span>
                  );
                }
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`nav-link ${active ? 'is-active' : ''}`}
                    aria-current={active ? 'page' : undefined}
                    onClick={onClose}
                  >
                    <Icon size={17} aria-hidden="true" />
                    {label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-foot">
          <p>Phase 2 preview</p>
          <p className="muted">Finance data shown is sample data.</p>
        </div>
      </aside>
    </>
  );
}

function UserMenu() {
  const { user, loading } = useCurrentUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointer(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const name = user?.full_name ?? (loading ? 'Loading…' : 'Account');

  return (
    <div className="user-menu" ref={ref}>
      <button
        className="user-menu-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="avatar" aria-hidden="true">
          {user ? initials(user.full_name) : <CircleUser size={18} />}
        </span>
        <span className="user-menu-name">{name}</span>
        <ChevronDown size={15} aria-hidden="true" />
      </button>

      {open && (
        <div className="user-menu-panel">
          {user && (
            <div className="user-menu-info">
              <p className="user-menu-info-name">{user.full_name}</p>
              <p className="muted">{user.email}</p>
              <div className="role-chips">
                {user.roles.map((r) => (
                  <span key={r} className="chip">{formatRole(r)}</span>
                ))}
              </div>
            </div>
          )}
          <div className="user-menu-foot">
            <SignOutButton />
          </div>
        </div>
      )}
    </div>
  );
}

function Topbar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="topbar">
      <button className="icon-btn topbar-menu" onClick={onMenu} aria-label="Open menu">
        <Menu size={20} />
      </button>

      <div className="topbar-actions">
        <UserMenu />
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <CurrentUserProvider>
      <div className="app-shell">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="app-main">
          <Topbar onMenu={() => setSidebarOpen(true)} />
          <main className="app-content">{children}</main>
        </div>
      </div>
    </CurrentUserProvider>
  );
}
