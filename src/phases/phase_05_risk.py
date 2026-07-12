"""
Phase 5: Risk — Risk management: Kelly, drawdown, SL/TP.
"""
from typing import Optional


class PhaseRisk:
    """Aplica gestión de riesgo antes de ejecutar el trade"""

    def __init__(self, config: dict):
        self.config = config

    def execute(self, ctx: dict, action: dict) -> Optional[dict]:
        """
        Verifica riesgo y calcula tamaño de posición.

        Returns:
            dict con {volumen, sl, tp, kelly_fraction} o None si bloquea
        """
        agent = ctx["agent"]

        # ¿Podemos operar?
        if not agent.risk.can_trade():
            ctx["risk_blocked"] = True
            return None

        # Calcular tamaño según Kelly
        kelly_fraction = agent.risk_cfg.get("kelly_fraction", 0.25)
        sl_pct = agent.risk_cfg.get("stop_loss_pct", 0.02)
        tp_pct = agent.risk_cfg.get("take_profit_pct", 0.04)

        capital = agent.balance_actual
        confidence = action.get("confidence", 0.5)
        base_volume = capital * kelly_fraction * confidence

        price = action.get("price", 0)
        volume = round(base_volume / max(price, 1), 4)

        risk_params = {
            "volume": max(volume, 0.0001),
            "sl": price * (1 - sl_pct) if price else 0,
            "tp": price * (1 + tp_pct) if price and tp_pct else 0,
            "kelly_fraction": kelly_fraction,
        }
        ctx["risk_params"] = risk_params
        return risk_params