import { useState, useMemo } from 'react'
import type { DashboardData } from './types'
import { useDashboard } from './hooks/useDashboard'
import { AgentCard } from './components/AgentCard'
import { OverallSummary } from './components/OverallSummary'
import { EquityChart, ComparisonView } from './components/Charts'
import { PositionsHistory } from './components/PositionsHistory'
import { AgentLog } from './components/AgentLog'

function Loading() {
  return (
    <main className="min-h-screen flex items-center justify-center" role="status">
      <p className="text-sm text-muted-foreground animate-pulse">Cargando...</p>
    </main>
  )
}

function ErrorView({ message }: { message: string }) {
  return (
    <main className="min-h-screen flex items-center justify-center p-4" role="alert">
      <div className="text-center max-w-md">
        <p className="text-2xl mb-2">⚠</p>
        <p className="text-sm mb-2">Error de conexión</p>
        <p className="text-xs text-muted-foreground">{message}</p>
      </div>
    </main>
  )
}

function DashboardInner({ data }: { data: DashboardData }) {
  const [activeAgents, setActiveAgents] = useState<Set<string>>(
    new Set(data.agents.map((a) => a.agent_id))
  )

  const sortedAgents = useMemo(
    () => [...data.agents].sort((a, b) => b.capital_pct - a.capital_pct),
    [data.agents]
  )

  const toggleAgent = (id: string) => {
    setActiveAgents((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a href="#main-content" className="skip-link">Saltar al contenido principal</a>

      <header className="border-b border-border px-4 py-3 sm:px-6" role="banner">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-foreground text-background text-[9px] font-semibold tracking-widest uppercase px-1.5 py-px inline-block">
              🏖️ Sandbox
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">PolypastaBot</h1>
              <p className="text-xs text-muted-foreground">Sistema multi-agente de trading</p>
            </div>
            <div className="text-[10px] text-muted-foreground tabular-nums">
              {data.last_updated && (
                <time dateTime={data.last_updated}>
                  {new Date(data.last_updated).toLocaleString()}
                </time>
              )}
            </div>
          </div>
        </div>
      </header>

      <main id="main-content" className="max-w-7xl mx-auto px-4 py-5 sm:px-6 space-y-6">
        <OverallSummary total={data.total} />

        {/* Agent cards — click to toggle */}
        <section aria-label="Agentes">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {sortedAgents.map((agent) => (
              <AgentCard
                key={agent.agent_id}
                agent={agent}
                active={activeAgents.has(agent.agent_id)}
                onToggle={() => toggleAgent(agent.agent_id)}
              />
            ))}
          </div>
          {activeAgents.size === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">
              Haz clic en un agente para ver sus datos
            </p>
          )}
        </section>

        {/* Charts & comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ComparisonView agents={sortedAgents} selectedAgents={activeAgents} />
          {data.history && data.history.length > 0 && (
            <EquityChart history={data.history} selectedAgents={activeAgents} />
          )}
        </div>

        {/* Positions & trade history */}
        <PositionsHistory agents={sortedAgents} trades={data.recent_trades} selectedAgents={activeAgents} />

        {/* Agent logs */}
        <AgentLog logs={data.agent_logs} tradeSummaries={data.trade_summaries} selectedAgents={activeAgents} />
      </main>

      <footer className="border-t border-border px-4 py-3 text-center text-[10px] text-muted-foreground">
        PolypastaBot · Los datos se actualizan cada 30 segundos
      </footer>
    </div>
  )
}

export default function App() {
  const { data, loading, error } = useDashboard()
  if (loading) return <Loading />
  if (error || !data) return <ErrorView message={error || 'Sin datos'} />
  return <DashboardInner data={data} />
}