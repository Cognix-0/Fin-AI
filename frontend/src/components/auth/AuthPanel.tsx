'use client';
import React from 'react';

/**
 * Left visual panel for auth pages.
 * Features:
 * - Animated SVG line chart representing financial data
 * - Brand logo mark
 * - One memorable headline
 * Design principle: one bold element (the chart), everything else quiet.
 */
export function AuthPanel() {
  // Simulated finance trend data points (two lines)
  const w = 400;
  const h = 220;

  // Revenue line (climbing trend)
  const revenue = [
    { x: 0,   y: 180 }, { x: 40,  y: 165 }, { x: 80,  y: 150 },
    { x: 120, y: 155 }, { x: 160, y: 130 }, { x: 200, y: 118 },
    { x: 240, y: 100 }, { x: 280, y: 88  }, { x: 320, y: 72  },
    { x: 360, y: 58  }, { x: 400, y: 42  },
  ];

  // Expenses line (slightly volatile)
  const expenses = [
    { x: 0,   y: 210 }, { x: 40,  y: 195 }, { x: 80,  y: 200 },
    { x: 120, y: 185 }, { x: 160, y: 175 }, { x: 200, y: 168 },
    { x: 240, y: 155 }, { x: 280, y: 160 }, { x: 320, y: 145 },
    { x: 360, y: 138 }, { x: 400, y: 125 },
  ];

  const toPath = (pts: { x: number; y: number }[]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  const toArea = (pts: { x: number; y: number }[], baseY: number) =>
    `${toPath(pts)} L ${pts[pts.length - 1].x} ${baseY} L ${pts[0].x} ${baseY} Z`;

  const months = ['Jan', 'Mar', 'May', 'Jul', 'Sep', 'Nov'];

  return (
    <div className="auth-panel-visual">
      {/* Logo */}
      <div className="logo">
        <div className="logo-mark">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M3 13 L7 8 L10 11 L15 5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span className="logo-text">FinanceOS</span>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '2rem' }}>
        <div>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>
            Company spending overview
          </p>
          <h2 style={{
            fontSize: 'clamp(1.5rem, 2.5vw, 2rem)',
            fontWeight: 600,
            color: 'var(--color-text-primary)',
            lineHeight: 1.25,
            maxWidth: '22ch',
          }}>
            Every expense, tracked and explained.
          </h2>
        </div>

        <div style={{ position: 'relative' }}>
          {/* Legend */}
          <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: '20px', height: '2px', background: 'var(--color-accent)', display: 'inline-block', borderRadius: '1px' }} />
              Revenue
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--color-text-secondary)' }}>
              <span style={{ width: '20px', height: '2px', background: '#8A9AC0', display: 'inline-block', borderRadius: '1px', opacity: 0.6 }} />
              Expenses
            </div>
          </div>

          <svg
            viewBox={`0 0 ${w} ${h}`}
            style={{ width: '100%', height: 'auto', overflow: 'visible' }}
            aria-hidden="true"
          >
            {/* Grid lines */}
            {[0, 55, 110, 165, 220].map((y) => (
              <line
                key={y}
                x1={0} y1={y} x2={w} y2={y}
                stroke="var(--color-border-subtle)"
                strokeWidth="1"
              />
            ))}

            {/* Expenses area fill */}
            <path
              d={toArea(expenses, h)}
              fill="rgba(138,154,192,0.06)"
            />

            {/* Revenue area fill */}
            <path
              d={toArea(revenue, h)}
              fill="rgba(59,127,245,0.08)"
            />

            {/* Expenses line */}
            <path
              d={toPath(expenses)}
              fill="none"
              stroke="rgba(138,154,192,0.45)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animate-line"
              style={{ animationDelay: '0.2s' }}
            />

            {/* Revenue line */}
            <path
              d={toPath(revenue)}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="animate-line"
            />

            {/* Revenue dots */}
            {revenue.filter((_, i) => i % 2 === 0).map((p, i) => (
              <circle
                key={i}
                cx={p.x} cy={p.y}
                r="3.5"
                fill="var(--color-accent)"
                opacity="0.9"
              />
            ))}

            {/* X-axis month labels */}
            {months.map((m, i) => (
              <text
                key={m}
                x={(i / (months.length - 1)) * w}
                y={h + 20}
                textAnchor="middle"
                fill="var(--color-text-muted)"
                fontSize="11"
                fontFamily="DM Sans, sans-serif"
              >
                {m}
              </text>
            ))}
          </svg>
        </div>

        {/* Stats row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
          {[
            { label: 'Total expenses', value: '$142K' },
            { label: 'Pending review', value: '23' },
            { label: 'Saved this month', value: '8.4%' },
          ].map(({ label, value }) => (
            <div key={label} style={{
              background: 'var(--color-surface-2)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              padding: '1rem',
            }}>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.375rem' }}>
                {label}
              </p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {value}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <p style={{ fontSize: '0.8125rem', color: 'var(--color-text-muted)' }}>
        AI-powered finance management for modern teams.
      </p>
    </div>
  );
}
