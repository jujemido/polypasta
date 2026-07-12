"""
Phase 8: Dashboard — Actualizar el JSON del dashboard + state persistente.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class PhaseDashboard:
    """Actualiza el dashboard y guarda estado persistente"""

    def __init__(self, config: dict):
        self.config = config
        self.dashboard_file = "data/dashboard_data.json"
        self.state_file = "data/state.json"

    def execute(self, results: dict, agents: list):
        """Escribe dashboard_data.json y state.json"""
        # Construir métricas
        data = {
            "last_updated": datetime.now().isoformat(),
            "total": self._get_total(agents),
            "agents": [a.get_metrics() for a in agents],
            "agent_logs": self._get_recent_logs(results),
            "training_logs": self._get_training_logs(results),
        }

        os.makedirs("data", exist_ok=True)
        with open(self.dashboard_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

        # State persistente
        state = {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                a.agent_id: {
                    "balance_actual": a.balance_actual,
                    "total_trades": getattr(a, "_total_trades", 0),
                    "win_trades": getattr(a, "_win_trades", 0),
                }
                for a in agents
            },
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _get_total(self, agents: list) -> dict:
        trading = [a for a in agents if not getattr(a, "_is_treasury", False)]
        treasury = next((a for a in agents if getattr(a, "_is_treasury", False)), None)
        total_bal = sum(a.balance_actual for a in trading)
        total_init = sum(a.balance_inicial for a in trading)
        treasury_bal = treasury.balance_actual if treasury else 0
        total_trd = sum(getattr(a, "_total_trades", 0) for a in trading)
        total_win = sum(getattr(a, "_win_trades", 0) for a in trading)
        return {
            "balance_inicial": round(total_init, 2),
            "balance_actual": round(total_bal + treasury_bal, 2),
            "trading_balance": round(total_bal, 2),
            "treasury_balance": round(treasury_bal, 2),
            "pnl_total": round(total_bal - total_init, 2),
            "pnl_pct": round((total_bal - total_init) / max(total_init, 0.01) * 100, 2),
            "total_trades": total_trd,
            "win_rate": round(total_win / max(total_trd, 1), 2),
            "agentes_activos": len([a for a in trading if getattr(a.risk, "can_trade", lambda: True)()]),
            "total_agentes": len(trading),
        }

    def _get_recent_logs(self, results: dict) -> list:
        logs = []
        for action in results.get("actions", []):
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": action.get("symbol", ""),
                "action": action.get("action", ""),
                "reason": action.get("reason", ""),
            })
        return logs[-200:]  # últimas 200

    def _get_training_logs(self, results: dict) -> list:
        return results.get("actions", [])[-500:]