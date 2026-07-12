"""
Agent Orchestrator — Ejecuta los agentes y consolida resultados.

1. Lee config de agents.yaml
2. Asigna capital a cada agente según su %
3. Ejecuta el ciclo de cada agente
4. Consolida resultados para dashboard
5. Escribe data/dashboard_data.json para el frontend React
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from src.agents.base import BaseAgent, AgentAction
from src.agents.conservative import ConservativeAgent
from src.agents.aggressive import AggressiveAgent
from src.agents.pessimistic import PessimisticAgent
from src.agents.long_term import LongTermAgent
from src.agents.treasury import TreasuryAgent
from src.learning.summary_logger import SummaryLogger
from src.learning.ai_validator import AIValidator
from src.utils.file_utils import log_error

AGENT_REGISTRY = {
    "conservative": ConservativeAgent,
    "aggressive": AggressiveAgent,
    "pessimistic": PessimisticAgent,
    "long_term": LongTermAgent,
    "treasury": TreasuryAgent,
}


class AgentOrchestrator:
    """
    Orquestador multi-agente. Gestiona creación, ejecución y monitoreo.
    """

    def __init__(self, config: dict, total_balance: float):
        self.cfg = config
        self.agents_cfg = config.get("agents", {})
        self.global_cfg = self.agents_cfg.get("committee", {})
        self.total_balance = total_balance

        self.agents: List[BaseAgent] = []
        self._create_agents()

        self.dashboard_data_file = self.global_cfg.get(
            "dashboard_data_file", "data/dashboard_data.json"
        )
        self._history: List[Dict] = []
        self._cycle = 0

        # Learning & validation
        self.summary_logger = SummaryLogger(config)
        self.ai_validator = AIValidator(config)
        self._recent_logs: List[Dict] = []
        self._training_logs: List[Dict] = []

        # Pipeline de phases
        self.pipeline = Pipeline(config, self.agents, None, None, None)

        # Restore state from disk
        state_file = "data/state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    state = json.load(f)
                for a in self.agents:
                    s = state.get("agents", {}).get(a.agent_id, {})
                    if s.get("balance_actual"):
                        a.balance_actual = s["balance_actual"]
                    if s.get("total_trades"):
                        a._total_trades = s["total_trades"]
                    if s.get("win_trades"):
                        a._win_trades = s["win_trades"]
                print(f"📦 Estado restaurado desde {state_file}")
            except Exception as e:
                print(f"⚠️  No se pudo restaurar state: {e}")

    def _create_agents(self):
        """Crea los agentes según la config"""
        for agent_id, agent_class in AGENT_REGISTRY.items():
            agent_cfg = self.agents_cfg.get(agent_id, {})
            if not agent_cfg.get("enabled", True):
                print(f"⏹️  Agent {agent_id} disabled in config")
                continue
            agent = agent_class(self.cfg, agent_cfg, self.total_balance)
            self.agents.append(agent)
            print(f"  ✅ {agent} — {', '.join(agent.symbols)}")

    # ─────────────────────────────────────────────
    # Ciclo principal
    # ─────────────────────────────────────────────

    def ejecutar_ciclo(self, broker) -> List[AgentAction]:
        """Ejecuta un ciclo de todos los agentes"""
        self._cycle += 1
        all_actions: List[AgentAction] = []
        cycle_start = datetime.now()

        print(f"\n🔄 Ciclo #{self._cycle} — {cycle_start.strftime('%H:%M:%S')}")
        print("─" * 40)

        for agent in self.agents:
            if agent.agent_id == "treasury":
                continue
            try:
                for symbol in agent.symbols:
                    df = broker.get_rates(symbol, agent.timeframe, agent.bars_to_fetch)
                    if df.empty:
                        continue

                    action = agent.analizar(broker, df, symbol)
                    if action is None:
                        continue

                    # AI validation if enabled
                    if self.ai_validator.enabled:
                        decision = self.ai_validator.validate(action)
                        if decision.get("blocked"):
                            print(f"  🚫 {agent.emoji} {agent.name}: {symbol} BLOQUEADO por IA")
                            print(f"     Motivo: {decision.get('reason', 'desconocido')}")
                            self.summary_logger.log(agent.agent_id, agent.name, symbol,
                                                     "blocked_by_ai", action)
                            continue

                    # Execute
                    result = agent.ejecutar(action, broker)
                    if result:
                        all_actions.append(action)
                        # Treasury: skim 20% of profit
                        treasury = next((a for a in self.agents if a.agent_id == "treasury"), None)
                        if treasury and hasattr(treasury, "process_profit") and action.tipo in ("buy", "sell"):
                            profit = result.get("profit", 0)
                            if profit > 0:
                                treasury.process_profit(agent.name, symbol, profit)

                        self.summary_logger.log(agent.agent_id, agent.name, symbol,
                                                 "executed", action)

                # Close positions with stopped-out SL/TP
                agent.cerrar_posiciones_vencidas(broker)

            except Exception as e:
                log_error(f"Error en {agent.name}: {e}")
                print(f"  ❌ {agent.emoji} {agent.name}: ERROR — {e}")

        # Actualizar dashboard
        self._actualizar_dashboard()

        total_pnl = sum(a.balance_actual - a.balance_inicial for a in self.agents if a.agent_id != "treasury")
        print(f"  ─────────────────────────────")
        print(f"  💰 P&L neto del ciclo: ${total_pnl:+.2f}")
        print(f"  📊 Dashboard actualizado → {self.dashboard_data_file}")

        return all_actions

    def _actualizar_dashboard(self):
        """Genera el JSON para el dashboard React"""
        data = self._build_dashboard_data()
        os.makedirs(os.path.dirname(self.dashboard_data_file), exist_ok=True)
        with open(self.dashboard_data_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        state_file = "data/state.json"
        os.makedirs("data", exist_ok=True)
        with open(state_file, "w") as f:
            state = {
                "timestamp": datetime.now().isoformat(),
                "agents": {
                    a.agent_id: {
                        "balance_actual": a.balance_actual,
                        "total_trades": a._total_trades,
                        "win_trades": a._win_trades,
                    }
                    for a in self.agents
                },
            }
            json.dump(state, f, indent=2, default=str)

    def _build_dashboard_data(self) -> Dict:
        """Construye el payload para el dashboard"""
        self._recent_logs = self.summary_logger.get_recent_logs(200)
        training = self.summary_logger.get_training_logs(500)
        return {
            "last_updated": datetime.now().isoformat(),
            "total": self._get_total_metrics(),
            "agents": [a.get_metrics() for a in self.agents],
            "agent_logs": self._recent_logs,
            "training_logs": training,
            "history": self._history,
        }

    def _get_total_metrics(self) -> Dict:
        """Métricas consolidadas de agentes + tesorería"""
        trading_agents = [a for a in self.agents if a.agent_id != "treasury"]
        treasury = next((a for a in self.agents if a.agent_id == "treasury"), None)
        total_balance = sum(a.balance_actual for a in trading_agents)
        total_initial = sum(a.balance_inicial for a in trading_agents)
        treasury_balance = treasury.balance_actual if treasury else 0
        total_trades = sum(a._total_trades for a in trading_agents)
        total_wins = sum(a._win_trades for a in trading_agents)

        return {
            "balance_inicial": round(total_initial, 2),
            "balance_actual": round(total_balance + treasury_balance, 2),
            "trading_balance": round(total_balance, 2),
            "treasury_balance": round(treasury_balance, 2),
            "pnl_total": round(total_balance - total_initial, 2),
            "pnl_pct": round((total_balance - total_initial) / max(total_initial, 0.01) * 100, 2),
            "total_trades": total_trades,
            "win_rate": round(total_wins / total_trades, 2) if total_trades > 0 else 0,
            "agentes_activos": len([a for a in trading_agents if a.risk.can_trade()]),
            "total_agentes": len(trading_agents),
        }

    def get_summary_text(self) -> str:
        lines = ["📊 <b>Resumen Multi-Agente</b>"]
        lines.append("─" * 30)
        for agent in self.agents:
            lines.append(agent.summary_line())
        lines.append("─" * 30)
        total = self._get_total_metrics()
        pnl_icon = "📈" if total["pnl_total"] >= 0 else "📉"
        lines.append(
            f"💰 <b>TOTAL</b>: ${total['balance_actual']:.2f} {pnl_icon} "
            f"{total['pnl_total']:+.2f} ({total['pnl_pct']:+.1f}%) "
            f"| {total['total_trades']} trades"
        )
        return "\n".join(lines)

    def __repr__(self):
        return f"🧠 AgentOrchestrator ({len(self.agents)} agentes)"