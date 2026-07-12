"""
Phase 3: Signals — Generar señales de trading según la estrategia del agente.
"""
from typing import Optional
from src.strategies.factory import get_strategy


class PhaseSignals:
    """Genera señales de trading usando la estrategia del agente"""

    def __init__(self, config: dict):
        self.config = config

    def execute(self, ctx: dict, df) -> Optional[dict]:
        """
        Analiza los indicadores y genera una señal (BUY/SELL/HOLD).

        Returns:
            dict con {tipo, simbolo, precio, confianza, razon} o None
        """
        from src.strategies.base import BaseStrategy

        agent = ctx["agent"]
        strategy = get_strategy(self.config, agent_id=agent.agent_id)
        if strategy is None:
            return None

        action = strategy.calculate_signals(df, symbol=ctx["symbol"])
        if action is None:
            return None

        ctx["action"] = action
        return action