import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

function MiniBar({ current, target }: { current: number; target: number }) {
  const pct = Math.min(100, (current / target) * 100)
  return (
    <div className="h-1 w-full bg-border rounded-full overflow-hidden" title={`${(current * 100).toFixed(0)}% vs objetivo ${(target * 100).toFixed(0)}%`}>
      <div className="h-full bg-foreground rounded-full transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

const STAR_COLORS = ['bg-foreground', 'bg-foreground/80', 'bg-foreground/60', 'bg-foreground/40', 'bg-foreground/20']

export function AgentCard({ agent, active, onToggle }: {
  agent: { agent_id: string; name: string; emoji?: string; capital_pct: number; balance_actual: number; pnl: number; pnl_pct: number; win_rate: number; total_trades: number; drawdown: number; open_positions: number; symbols: string[]; timeframe: string; risk_stars: number; target_win_rate: number; status: string }
  active: boolean; onToggle: () => void
}) {
  const pnlPositive = agent.pnl >= 0

  return (
    <Card
      className={`cursor-pointer select-none transition-all rounded-xl ${
        active
          ? 'ring-1 ring-foreground/20 shadow-sm bg-card'
          : 'opacity-35 hover:opacity-55 bg-muted/30'
      }`}
      onClick={onToggle}
      onKeyDown={(e) => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); onToggle() } }}
      tabIndex={0}
      role="switch"
      aria-checked={active}
    >
      <CardContent className="p-3.5 space-y-2.5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold">{agent.name}</span>
          </div>
          <Badge variant={active ? 'default' : 'secondary'} className="text-[9px] leading-none py-px px-1.5">
            {active ? 'activo' : 'oculto'}
          </Badge>
        </div>

        {/* Markets */}
        {active && (
          <>
            <p className="text-[10px] text-muted-foreground truncate">{agent.symbols.slice(0, 4).join(', ')}{agent.symbols.length > 4 ? ` +${agent.symbols.length - 4}` : ''}</p>

            {/* Stats grid */}
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">Capital</span><span className="font-medium tabular-nums">${agent.balance_actual.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Asignado</span><span className="font-medium">{(agent.capital_pct * 100).toFixed(0)}%</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">P&L</span><span className={`font-medium tabular-nums ${pnlPositive ? '' : 'opacity-60'}`}>{agent.pnl >= 0 ? '+' : ''}{agent.pnl.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Rentab.</span><span className={`font-medium tabular-nums ${pnlPositive ? '' : 'opacity-60'}`}>{agent.pnl_pct >= 0 ? '+' : ''}{agent.pnl_pct.toFixed(1)}%</span></div>
            </div>

            {/* Win rate vs target */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-muted-foreground">Win rate</span>
                <span className="font-medium">{(agent.win_rate * 100).toFixed(0)}% / {(agent.target_win_rate * 100).toFixed(0)}% obj.</span>
              </div>
              <MiniBar current={agent.win_rate} target={agent.target_win_rate} />
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-0.5">
              <span><span className="text-foreground/60 font-medium">TF</span> {agent.timeframe}</span>
              <span className="flex items-center gap-1.5">
                <span className="flex gap-px">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <span key={i} className={`block h-2.5 w-[2.5px] rounded-sm ${i <= agent.risk_stars ? STAR_COLORS[agent.risk_stars - 1] || 'bg-foreground' : 'bg-border'}`} />
                  ))}
                </span>
                <span><span className="text-foreground/60">Pos</span> {agent.open_positions}</span>
                <span><span className="text-foreground/60">DD</span> {(agent.drawdown * 100).toFixed(1)}%</span>
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}