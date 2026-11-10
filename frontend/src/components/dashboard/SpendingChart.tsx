'use client';
import { useState } from 'react';
import { MonthlySpend } from '@/types/finance';
import { formatMoney, formatMoneyCompact } from '@/lib/format';

interface Props {
  data: MonthlySpend[];
  highlightLast: number;   // number of trailing months in the selected period
}

function niceMax(n: number) {
  const step = 10 ** Math.floor(Math.log10(n));
  return Math.ceil(n / step) * step;
}

export function SpendingChart({ data, highlightLast }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  // Guard against an all-zero series (new install, no expenses yet)
  const max = niceMax(Math.max(1, ...data.map((d) => d.amount)));
  const ticks = [max, max / 2, 0];
  const firstHighlighted = data.length - highlightLast;

  return (
    <div className="bar-chart">
      <div className="bar-chart-plot">
        {ticks.map((t) => (
          <div key={t} className="bar-chart-grid" style={{ bottom: `${(t / max) * 100}%` }}>
            <span>{formatMoneyCompact(t)}</span>
          </div>
        ))}

        <div className="bar-chart-bars">
          {data.map((d, i) => {
            const inPeriod = i >= firstHighlighted;
            return (
              <div
                key={d.month}
                className="bar-chart-col"
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                tabIndex={0}
                aria-label={`${d.label}: ${formatMoney(d.amount)}`}
              >
                <div
                  className={`bar ${inPeriod ? 'is-active' : ''} ${hover === i ? 'is-hover' : ''}`}
                  style={{ height: `${(d.amount / max) * 100}%` }}
                />
                {hover === i && (
                  <div className="chart-tooltip" role="tooltip">
                    <strong>{formatMoney(d.amount)}</strong>
                    <span>{d.label} {d.month.slice(0, 4)}{inPeriod ? ' · in selected period' : ''}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="bar-chart-labels" aria-hidden="true">
        {data.map((d) => <span key={d.month}>{d.label}</span>)}
      </div>

      {/* Screen-reader / table view of the same data */}
      <table className="sr-only">
        <caption>Monthly spending</caption>
        <thead><tr><th>Month</th><th>Amount</th></tr></thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.month}><td>{d.label} {d.month.slice(0, 4)}</td><td>{formatMoney(d.amount)}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
