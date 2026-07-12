"""
Treasury Agent — Protector de beneficios.

Nunca hace trading. Solo recoge un % de cada beneficio y lo guarda
en una hucha protegida que nunca se toca.

Reglas:
  - Cada vez que un agente cierra un trade con BENEFICIO:
      treasury += profit × treasury_pct
      trading  -= profit × treasury_pct  (el beneficio neto se reduce)
  - Si el trade es pérdida → la tesorería NO se toca
  - La tesorería nunca se usa para trading
"""

from typing import Optional
from src.agents.base import BaseAgent, AgentAction


class TreasuryAgent(BaseAgent):
    """
    Agente Tesorero — No tradea, solo protege beneficios.

    Se muestra en el dashboard como un "agente" más pero
    con la particularidad de que su balance solo sube (nunca baja).
    """

    agent_id = "treasury"
    name = "Tesorero"
    emoji = "💰"
    description = "Protege beneficios — 20% de cada ganancia a la hucha"

    def __init__(self, config: dict, agent_cfg: dict, total_balance: float):
        super().__init__(config, agent_cfg, total_balance)

        # El tesorero no tiene capital asignado "para trading"
        # En lugar de eso, acumula desde 0
        self.capital_asignado = 0.0
        self.balance_inicial = 0.0
        self.balance_actual = 0.0

        # % de cada beneficio que va a tesorería (configurable)
        self.treasury_pct = agent_cfg.get("treasury_pct", 0.20)

        # Estadísticas
        self._total_skimmed = 0.0
        self._times_skimmed = 0

        # Flags para que el orquestador no intente hacerle trade
        self._is_treasury = True

    def analizar(self, broker, df, symbol) -> Optional[AgentAction]:
        """El tesorero nunca tradea"""
        return None

    def ejecutar_ciclo(self, broker) -> Optional[AgentAction]:
        """El tesorero no tiene ciclo de trading"""
        return None

    # ─────────────────────────────────────────────
    # Método principal: procesar beneficio
    # ─────────────────────────────────────────────

    def process_profit(self, agent_name: str, symbol: str, profit: float) -> dict:
        """
        Procesa un beneficio cerrado por cualquier agente.

        Args:
            agent_name: Nombre del agente que generó el beneficio
            symbol: Símbolo operado
            profit: Beneficio REAL (positivo = ganancia, negativo = pérdida)

        Returns:
            {"skimmed": float, "treasury_before": float, "treasury_after": float}
            o {"skimmed": 0, "reason": "no_profit"} si es pérdida
        """
        if profit <= 0:
            return {"skimmed": 0, "reason": "no_profit"}

        skim = round(profit * self.treasury_pct, 2)
        before = self.balance_actual

        self.balance_actual += skim
        self._total_skimmed += skim
        self._times_skimmed += 1

        print(f"💰 TESORERO: {agent_name} ganó ${profit:.2f} → "
              f"${skim:.2f} ({self.treasury_pct:.0%}) a la hucha "
              f"(hucha: ${before:.2f} → ${self.balance_actual:.2f})")

        return {
            "skimmed": skim,
            "treasury_before": before,
            "treasury_after": self.balance_actual,
            "reason": "profit_skimmed",
            "agent": agent_name,
            "symbol": symbol,
        }

    # ─────────────────────────────────────────────
    # Métricas override
    # ─────────────────────────────────────────────

    def get_metrics(self) -> dict:
        base = super().get_metrics()
        base.update({
            "treasury_pct": self.treasury_pct,
            "total_skimmed": round(self._total_skimmed, 2),
            "times_skimmed": self._times_skimmed,
            "capital_pct": 0,  # No capital asignado inicial
            "symbols": ["Todas las ganancias"],
            "timeframe": "—",
            "risk_stars": 0,
            "target_win_rate": 1.0,
            "total_trades": 0,
            "win_rate": 0,
        })
        return base

    def summary_line(self) -> str:
        m = self.get_metrics()
        return (
            f"{self.emoji} <b>{self.name}</b>: "
            f"${m['balance_actual']:.2f} protegidos "
            f"({m['total_skimmed']:.2f} skimmed de {m['times_skimmed']} trades)"
        )

    def __repr__(self):
        return f"{self.emoji} {self.name} ({self.treasury_pct:.0%} de profits)"