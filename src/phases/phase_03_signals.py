"""
Phase 3: Signals — Generar señales de trading según la estrategia del agente.

Cada agente tiene su propia lógica de análisis inline (analizar()).
Esta fase simplemente llama al método del agente.
"""
from typing import Optional


class PhaseSignals:
    """Genera señales de trading llamando a agent.analizar()"""

    def __init__(self, config: dict):
        self.config = config

    def execute(self, ctx: dict, df) -> Optional[dict]:
        """
        Analiza los indicadores y genera una señal (BUY/SELL/HOLD).

        Returns:
            dict con {tipo, simbolo, precio, confianza, razon} o None si no hay señal
        """
        agent = ctx["agent"]
        broker = ctx.get("broker")

        action = agent.analizar(broker, df, ctx["symbol"])
        if action is None:
            return None

        ctx["action"] = action
        return action