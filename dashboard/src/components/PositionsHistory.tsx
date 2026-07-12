import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import type { AgentMetric, Trade } from '../types'

/* ── Positions table ── */

function PositionsTable({ agents, selected }: { agents: AgentMetric[]; selected: Set<string> }) {
  const rows = useMemo(
    () => agents
      .filter((a) => selected.has(a.agent_id) && a.positions?.length)
      .flatMap((a) => (a.positions ?? []).map((p) => ({ ...p, agent_name: a.name }))),
    [agents, selected]
  )

  if (!rows.length) {
    return <p className="text-sm text-muted-foreground text-center py-8">Sin posiciones abiertas</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="text-xs">Agente</TableHead>
          <TableHead className="text-xs">Símbolo</TableHead>
          <TableHead className="text-xs">Dir</TableHead>
          <TableHead className="text-right text-xs">Entry</TableHead>
          <TableHead className="text-right text-xs">Actual</TableHead>
          <TableHead className="text-right text-xs">P&amp;L</TableHead>
          <TableHead className="text-right text-xs">Duración</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((p) => (
          <TableRow key={p.ticket}>
            <TableCell className="text-xs">{p.agent_name}</TableCell>
            <TableCell className="text-xs font-medium">{p.symbol}</TableCell>
            <TableCell>
              <Badge variant={p.direction === 'buy' ? 'default' : 'secondary'} className="text-[10px]">
                {p.direction === 'buy' ? 'L' : 'S'}
              </Badge>
            </TableCell>
            <TableCell className="text-right text-xs tabular-nums">{p.entry_price.toFixed(1)}</TableCell>
            <TableCell className="text-right text-xs tabular-nums">{p.current_price.toFixed(1)}</TableCell>
            <TableCell className={`text-right text-xs tabular-nums font-medium ${p.pnl >= 0 ? '' : 'opacity-60'}`}>
              {p.pnl >= 0 ? '+' : ''}{p.pnl.toFixed(2)}
            </TableCell>
            <TableCell className="text-right text-xs text-muted-foreground">{p.duration}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/* ── Trades table ── */

function TradesTable({ trades, selected }: { trades: Trade[]; selected: Set<string> }) {
  const rows = useMemo(
    () => trades.filter((t) => selected.has(t.agent_id)).slice(0, 20),
    [trades, selected]
  )

  if (!rows.length) {
    return <p className="text-sm text-muted-foreground text-center py-8">Sin actividad reciente</p>
  }

  return (
    <div className="max-h-[300px] overflow-y-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-card">
          <TableRow>
            <TableHead className="text-xs">Hora</TableHead>
            <TableHead className="text-xs">Agente</TableHead>
            <TableHead className="text-xs">Símbolo</TableHead>
            <TableHead className="text-xs">Acción</TableHead>
            <TableHead className="text-right text-xs">P&amp;L</TableHead>
            <TableHead className="text-right text-xs">Motivo</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((t, i) => (
            <TableRow key={`${t.timestamp}-${i}`}>
              <TableCell className="text-xs text-muted-foreground tabular-nums">
                {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </TableCell>
              <TableCell className="text-xs">{t.agent_name}</TableCell>
              <TableCell className="text-xs font-medium">{t.symbol}</TableCell>
              <TableCell>
                <Badge variant={t.action === 'buy' ? 'default' : 'secondary'} className="text-[10px]">
                  {t.action === 'buy' ? 'COMPRA' : 'VENTA'}
                </Badge>
              </TableCell>
              <TableCell className={`text-right text-xs tabular-nums font-medium ${t.exit_reason === 'abierto' ? '' : (t.profit >= 0 ? '' : 'opacity-60')}`}>
                {t.exit_reason === 'abierto' ? '—' : `${t.profit >= 0 ? '+' : ''}${t.profit.toFixed(2)}`}
              </TableCell>
              <TableCell className="text-right text-xs text-muted-foreground truncate max-w-[120px]" title={t.reason}>
                {t.reason}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

/* ── Composed ── */

export function PositionsHistory({
  agents, trades, selectedAgents,
}: {
  agents: AgentMetric[]
  trades?: Trade[]
  selectedAgents: Set<string>
}) {
  return (
    <section aria-label="Posiciones e historial">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Posiciones e historial</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <Tabs defaultValue="positions">
            <TabsList className="mb-3">
              <TabsTrigger value="positions">Posiciones abiertas</TabsTrigger>
              <TabsTrigger value="trades">Últimos trades</TabsTrigger>
            </TabsList>
            <TabsContent value="positions">
              <PositionsTable agents={agents} selected={selectedAgents} />
            </TabsContent>
            <TabsContent value="trades">
              {trades?.length ? (
                <TradesTable trades={trades} selected={selectedAgents} />
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">Sin actividad</p>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </section>
  )
}