"""
Agent Orchestrator — Ejecuta los 4 agentes en paralelo y consolida resultados.

El orquestador:
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
import time

from src.agents.base import BaseAgent, AgentAction
from src.agents.conservative import ConservativeAgent
from src.agents.aggressive import AggressiveAgent
from src.agents.pessimistic import PessimisticAgent
from src.agents.long_term import LongTermAgent
from src.agents.treasury import TreasuryAgent
from src.utils.file_utils import log_error


# Registry: agent_id → clase
AGENT_REGISTRY = {
    "conservative": ConservativeAgent,
    "aggressive": AggressiveAgent,
    "pessimistic": PessimisticAgent,
    "long_term": LongTermAgent,
    "treasury": TreasuryAgent,
}


class AgentOrchestrator:
    """
    Orquestador multi-agente.

    Gestiona la creacion, ejecución y monitoreo de todos los agentes.
    """

    def __init__(self, config: dict, total_balance: float):
        self.cfg = config
        self.agents_cfg = config.get("agents", {})
        self.global_cfg = self.agents_cfg.get("committee", {})
        self.total_balance = total_balance

        # Crear agentes
        self.agents: List[BaseAgent] = []
        self._create_agents()

        # Data para dashboard
        self.dashboard_data_file = self.global_cfg.get(
            "dashboard_data_file", "data/dashboard_data.json"
        )
        self._history: List[Dict] = []
        self._cycle = 0

        # Logger de summaries
        from src.learning.summary_logger import SummaryLogger
        self.summary_logger = SummaryLogger(config)
        self._recent_logs: List[Dict] = []

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
        """
        Ejecuta un ciclo completo de todos los agentes.

        Args:
            broker: Conexión al broker

        Returns:
            Lista de acciones ejecutadas
        """
        self._cycle += 1
        acciones_ejecutadas = []

        for agent in self.agents:
            try:
                action = agent.ejecutar_ciclo(broker)
                if action:
                    # Ejecutar
                    ticket = agent.ejecutar_action(broker, action)
                    if ticket:
                        acciones_ejecutadas.append(action)
                        print(f"\n{action}")
                    else:
                        print(f"  ⚠️ {agent.emoji} {agent.name}: acción {action.action} {action.symbol} falló")
            except Exception as e:
                error_msg = f"{agent.emoji} {agent.name}: {e}"
                print(f"  ❌ {error_msg}")
                log_error("data/logs/errors.log", error_msg, {"agent": agent.agent_id})

        # Actualizar dashboard
        self._actualizar_dashboard()

        return acciones_ejecutadas

    # ─────────────────────────────────────────────
    # Dashboard data
    # ─────────────────────────────────────────────

    def _actualizar_dashboard(self):
        """Escribe datos para el dashboard React"""
        data = self._build_dashboard_data()

        # Añadir a histórico (máx 500 puntos)
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "cycle": self._cycle,
            "agents": {a.agent_id: a.get_metrics() for a in self.agents},
            "total": self._get_total_metrics(),
        }
        self._history.append(snapshot)
        if len(self._history) > 500:
            self._history = self._history[-500:]

        data["history"] = self._history

        # Escribir a JSON
        os.makedirs(os.path.dirname(self.dashboard_data_file), exist_ok=True)
        with open(self.dashboard_data_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        # Guardar estado persistent (no volátil)
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
        return {
            "last_updated": datetime.now().isoformat(),
            "total": self._get_total_metrics(),
            "agents": [a.get_metrics() for a in self.agents],
            "agent_logs": self._recent_logs,
            "history": [],
        }

    def _get_total_metrics(self) -> Dict:
        """Métricas consolidadas de todos los agentes + tesorería"""
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
            "pnl_pct": round((total_balance - total_initial) / total_initial * 100 if total_initial > 0 else 0, 2),
            "total_trades": total_trades,
            "win_rate": round(total_wins / total_trades, 2) if total_trades > 0 else 0,
            "agentes_activos": len([a for a in self.agents if a.risk.can_trade()]),
            "total_agentes": len([a for a in self.agents if a.agent_id != "treasury"]),
        }

    # ─────────────────────────────────────────────
    # Reportes
    # ─────────────────────────────────────────────

    def get_summary_text(self) -> str:
        """Texto de resumen para Telegram"""
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