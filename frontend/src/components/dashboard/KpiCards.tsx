import { TrendingDown, TrendingUp } from 'lucide-react';

export interface Kpi {
  label: string;
  value: string;
  detail: string;
  delta?: number;       // % change vs previous period
}

export function KpiCards({ items }: { items: Kpi[] }) {
  return (
    <section className="kpi-grid" aria-label="Key figures">
      {items.map((kpi) => (
        <div key={kpi.label} className="card kpi">
          <p className="kpi-label">{kpi.label}</p>
          <p className="kpi-value">{kpi.value}</p>
          <p className="kpi-detail">
            {kpi.delta !== undefined && (
              <span className="kpi-delta">
                {kpi.delta >= 0
                  ? <TrendingUp size={14} aria-hidden="true" />
                  : <TrendingDown size={14} aria-hidden="true" />}
                {kpi.delta >= 0 ? '+' : ''}{kpi.delta.toFixed(1)}%
              </span>
            )}
            {kpi.detail}
          </p>
        </div>
      ))}
    </section>
  );
}

