import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import type { HistorySnapshot, AgentMetric } from '../types'

const GRAYSCALE: Record<string, string> = {
  conservative: '#000000', aggressive: '#444444',
  pessimistic: '#777777', long_term: '#aaaaaa',
}

export function EquityChart({
  history, selectedAgents,
}: { history: HistorySnapshot[]; selectedAgents: Set<string> }) {
  if (!history?.length) return null

  const data = history.map((h) => {
    const pt: Record<string, unknown> = {
      name: new Date(h.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' }),
      Total: h.total.balance_actual,
      Treasury: h.total.treasury_balance ?? 0,
    }
    for (const [id, a] of Object.entries(h.agents))
      if (selectedAgents.has(id)) pt[id] = a.balance_actual
    return pt
  })

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>Curva de capital</CardTitle></CardHeader>
      <CardContent>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="2 2" stroke="#ccc" />
              <XAxis dataKey="name" stroke="#555" fontSize={11} tickLine={false} />
              <YAxis stroke="#555" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ border: '1px solid #000', borderRadius: 4, fontSize: 12 }}
                formatter={(v, n) => [`$${Number(v).toFixed(2)}`, n]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Total" stroke="#000" strokeWidth={2} dot={false} name="Total" />
              {selectedAgents.has('conservative') && <Line type="monotone" dataKey="conservative" stroke={GRAYSCALE.conservative} strokeWidth={1.5} dot={false} name="Conservador" />}
              {selectedAgents.has('aggressive') && <Line type="monotone" dataKey="aggressive" stroke={GRAYSCALE.aggressive} strokeWidth={1.5} dot={false} name="Agresivo" />}
              {selectedAgents.has('pessimistic') && <Line type="monotone" dataKey="pessimistic" stroke={GRAYSCALE.pessimistic} strokeWidth={1.5} dot={false} name="Pesimista" />}
              {selectedAgents.has('long_term') && <Line type="monotone" dataKey="long_term" stroke={GRAYSCALE.long_term} strokeWidth={1.5} dot={false} name="Largo Plazo" />}
              <Line type="monotone" dataKey="Treasury" stroke="#888" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="💰 Tesorería" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

export function ComparisonView({
  agents, selectedAgents,
}: { agents: AgentMetric[]; selectedAgents: Set<string> }) {
  const filtered = agents.filter((a) => selectedAgents.has(a.agent_id))
  const metrics: { key: keyof AgentMetric; label: string; fmt: (v: number) => string }[] = [
    { key: 'pnl_pct', label: 'Rentabilidad', fmt: (v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` },
    { key: 'win_rate', label: 'Win rate', fmt: (v) => `${(v * 100).toFixed(0)}%` },
    { key: 'total_trades', label: 'Trades', fmt: (v) => v.toString() },
    { key: 'drawdown', label: 'Drawdown', fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: 'balance_actual', label: 'Capital', fmt: (v) => `$${v.toFixed(2)}` },
  ]

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>Comparación</CardTitle></CardHeader>
      <CardContent>
        {filtered.length < 2 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">Selecciona al menos 2 agentes</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Métrica</TableHead>
                {filtered.map((a) => (
                  <TableHead key={a.agent_id} className="text-right text-xs">
                    {a.name.split(' ').slice(1).join(' ')}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {metrics.map((m) => (
                <TableRow key={m.label}>
                  <TableCell className="text-xs text-muted-foreground font-medium">{m.label}</TableCell>
                  {filtered.map((a) => (
                    <TableCell key={a.agent_id} className="text-right text-xs tabular-nums">
                      {m.fmt(a[m.key] as number)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}