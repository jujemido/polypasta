import type { TotalMetric } from '../types'

function Trend({ value, label }: { value: number; label?: string }) {
  const up = value >= 0
  return (
    <span className={`inline-flex items-center gap-0.5 text-[11px] font-medium ${up ? 'text-foreground' : 'text-muted-foreground'}`}>
      <span className="text-[9px]">{up ? '▲' : '▼'}</span>
      {Math.abs(value).toFixed(1)}%{label && <span className="text-muted-foreground/60 font-normal ml-0.5">{label}</span>}
    </span>
  )
}

export function OverallSummary({ total }: { total: TotalMetric }) {
  const pnlPositive = total.pnl_total >= 0
  const cards = [
    { label: 'Balance total', value: `$${total.balance_actual.toFixed(2)}`, large: true },
    { label: 'Trading', value: `$${(total.trading_balance ?? total.balance_actual).toFixed(2)}`, sub: 'Capital operativo' },
    { label: '💰 Tesorería', value: `$${(total.treasury_balance ?? 0).toFixed(2)}`, sub: 'Protegido' },
    { label: 'P&L Total', value: `${pnlPositive ? '+' : ''}$${total.pnl_total.toFixed(2)}`, trend: total.pnl_pct, sub: 'vs capital inicial' },
    { label: 'Win Rate', value: `${(total.win_rate * 100).toFixed(0)}%`, sub: `${total.total_trades} trades` },
    { label: 'Agentes', value: `${total.agentes_activos}/${total.total_agentes}`, sub: 'activos' },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="bg-card rounded-xl border border-border p-3.5 space-y-1">
          <p className="text-[11px] font-medium text-muted-foreground tracking-wide">{c.label}</p>
          <p className={`font-bold tabular-nums ${c.large ? 'text-2xl' : 'text-lg'}`}>{c.value}</p>
          <div className="flex items-center gap-2">
            {c.trend !== undefined && <Trend value={c.trend} />}
            {c.sub && <span className="text-[10px] text-muted-foreground/60">{c.sub}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}