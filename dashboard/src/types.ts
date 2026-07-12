export interface AgentMetric {
  agent_id: string
  name: string
  capital_pct: number
  capital_inicial: number
  balance_actual: number
  pnl: number
  pnl_pct: number
  win_rate: number
  total_trades: number
  drawdown: number
  open_positions: number
  symbols: string[]
  timeframe: string
  risk_stars: number
  target_win_rate: number
  status: string
  positions?: Position[]
}

export interface Position {
  symbol: string; direction: 'buy' | 'sell'; volume: number
  entry_price: number; current_price: number; pnl: number
  pnl_pct: number; duration: string; ticket: number
}

export interface Trade {
  timestamp: string; agent_id: string; agent_name: string
  symbol: string; action: 'buy' | 'sell'; volume: number
  price: number; profit: number; profit_pct: number
  reason: string; exit_reason?: string
}

export interface AgentLogEntry {
  timestamp: string
  agent_id: string
  agent_name: string
  symbol: string
  indicators: string
  conclusion: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  action: 'executed' | 'skipped' | 'blocked_by_ai'
  reason: string
}

export interface TradeSummaryEntry {
  timestamp: string
  period: string
  total_trades: number
  wins: number
  losses: number
  win_rate: number
  total_profit: number
  best_trade: string
  worst_trade: string
  agent_performance: { agent: string; profit: number; trades: number }[]
  ai_analysis: string
  recommendations: string[]
}

export interface TotalMetric {
  balance_inicial: number; balance_actual: number
  trading_balance?: number; treasury_balance?: number
  pnl_total: number; pnl_pct: number
  total_trades: number; win_rate: number
  agentes_activos: number; total_agentes: number
}

export interface HistorySnapshot {
  timestamp: string; cycle: number
  total: { balance_actual: number; pnl_total: number; treasury_balance?: number }
  agents: Record<string, { pnl: number; balance_actual: number; total_trades: number }>
}

export interface DashboardData {
  last_updated?: string
  total: TotalMetric
  agents: AgentMetric[]
  recent_trades?: Trade[]
  agent_logs?: AgentLogEntry[]
  trade_summaries?: TradeSummaryEntry[]
  history?: HistorySnapshot[]
}