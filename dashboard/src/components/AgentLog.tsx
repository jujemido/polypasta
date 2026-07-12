import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { AgentLogEntry, TradeSummaryEntry } from '../types'

const PAGE_SIZE = 20

/* ── Tooltips para cada término ── */
const LABELS: Record<string, { label: string; tip: string }> = {
  BUY:  { label: 'COMPRA', tip: 'Señal de compra: el agente cree que el precio subirá' },
  SELL: { label: 'VENTA', tip: 'Señal de venta: el agente cree que el precio bajará' },
  HOLD: { label: 'ESPERAR', tip: 'Sin señal: el agente no encuentra condiciones favorables' },
  executed:    { label: 'EJECUTADO', tip: 'La operación se ejecutó correctamente' },
  skipped:    { label: 'SALTADO', tip: 'El agente decidió no actuar (confianza baja)' },
  blocked_by_ai: { label: 'BLOQUEADO', tip: 'La IA revisó y bloqueó la operación por seguridad' },
}

/* ── Tooltip inline (title nativo) ── */
function T({ label, tip }: { label: string; tip: string }) {
  return <span className="border-b border-dotted border-muted-foreground/40 cursor-help" title={tip}>{label}</span>
}

/* ── Agent Log ── */
export function AgentLog({
  logs, selectedAgents, tradeSummaries,
}: {
  logs?: AgentLogEntry[]
  selectedAgents: Set<string>
  tradeSummaries?: TradeSummaryEntry[]
}) {
  const [page, setPage] = useState(0)

  const filtered = useMemo(
    () => (logs ?? []).filter((l) => selectedAgents.has(l.agent_id)),
    [logs, selectedAgents]
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages - 1)
  const pageLogs = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE)

  if (!logs?.length && !tradeSummaries?.length) {
    return (
      <Card>
        <CardHeader className="pb-2"><CardTitle>Actividad</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-6">Sin actividad registrada aún</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle>Actividad de agentes</CardTitle>
          <span className="text-xs text-muted-foreground tabular-nums">
            {safePage * PAGE_SIZE + 1}–{Math.min((safePage + 1) * PAGE_SIZE, filtered.length)} de {filtered.length}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        {/* Trade summaries (IA) */}
        {tradeSummaries && tradeSummaries.length > 0 && (
          <div className="space-y-3 pb-3 border-b border-border">
            {tradeSummaries.slice(0, 3).map((s, i) => (
              <div key={i} className="bg-muted rounded-lg p-3 space-y-1.5 text-xs">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="default" className="text-[9px] bg-foreground text-background">IA</Badge>
                  <span className="font-semibold">Resumen {s.period}</span>
                  <span className="text-[10px] text-muted-foreground/60">
                    {new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <span className="text-muted-foreground ml-auto">
                    {s.wins}/{s.losses} · {s.win_rate}% · ${s.total_profit.toFixed(2)}
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed">{s.ai_analysis}</p>
                {s.recommendations.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {s.recommendations.map((r, j) => (
                      <span key={j} className="text-[10px] bg-border px-1.5 py-0.5 rounded" title="Recomendación generada por IA">
                        💡 {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Agent logs */}
        {pageLogs.map((entry, i) => {
          const conl = LABELS[entry.conclusion] ?? { label: entry.conclusion, tip: '' }
          const actl = LABELS[entry.action] ?? { label: entry.action, tip: '' }
          return (
            <div key={`${entry.timestamp}-${i}`} className="text-xs border-b border-border/40 pb-2.5 last:border-0">
              <div className="flex items-start gap-2 mb-1">
                <span className="text-muted-foreground tabular-nums mt-0.5 shrink-0 w-10">
                  {new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                    <span className="font-semibold text-foreground">{entry.agent_name}</span>
                    <Badge variant={entry.conclusion === 'BUY' ? 'default' : 'secondary'} className="text-[9px] leading-none py-px cursor-help" title={conl.tip}>
                      <T label={conl.label} tip={conl.tip} />
                    </Badge>
                    <Badge variant={entry.action === 'executed' ? 'default' : (entry.action === 'blocked_by_ai' ? 'secondary' : 'outline')}
                           className={`text-[9px] leading-none py-px cursor-help ${entry.action === 'blocked_by_ai' ? 'opacity-70 border-foreground/30' : ''}`}
                           title={actl.tip}>
                      <T label={actl.label} tip={actl.tip} />
                    </Badge>
                    <span className="text-foreground/70 font-medium">{entry.symbol}</span>
                    <span className="text-muted-foreground ml-auto shrink-0" title="Confianza del agente en esta señal">
                      🎯 {Math.round(entry.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-muted-foreground/70 leading-relaxed">
                    <span className="text-foreground/40" title="Indicadores técnicos en el momento del análisis">📐</span>{' '}
                    {entry.indicators}
                  </p>
                  <p className="text-muted-foreground leading-relaxed">
                    <span className="text-foreground/40" title="Razón de la decisión">💬</span>{' '}
                    {entry.reason}
                  </p>
                </div>
              </div>
            </div>
          )
        })}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <Button variant="outline" size="sm" disabled={safePage === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    className="text-xs h-7">← Anterior</Button>
            <span className="text-xs text-muted-foreground tabular-nums">
              Pág. {safePage + 1} / {totalPages}
            </span>
            <Button variant="outline" size="sm" disabled={safePage >= totalPages - 1}
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    className="text-xs h-7">Siguiente →</Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}