"""
Phase 6: Execution — Ejecutar el trade contra el broker.
"""
from typing import Optional


class PhaseExecution:
    """Ejecuta la orden de trading contra el broker"""

    def __init__(self, broker, config: dict):
        self.broker = broker
        self.config = config

    def execute(self, ctx: dict, risk_params: dict) -> Optional[dict]:
        """
        Ejecuta el trade.

        Returns:
            dict con {ticket, symbol, tipo, precio, volumen, profit} o None
        """
        from src.agents.base import AgentAction

        action = ctx["action"]
        agent = ctx["agent"]

        order_type = "buy" if action.get("tipo") in ("buy", "BUY", 0) else "sell"
        symbol = action.get("symbol", ctx["symbol"])
        price = action.get("price", 0)
        volume = risk_params["volume"]
        sl = risk_params.get("sl", 0)
        tp = risk_params.get("tp", 0)

        ticket = self.broker.open_trade(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            sl=sl,
            tp=tp,
            comment=f"{agent.emoji} {agent.name}",
        )

        if ticket is None:
            return None

        result = {
            "ticket": ticket,
            "symbol": symbol,
            "type": order_type,
            "price": price,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "profit": 0.0,  # Se actualiza al cerrar
        }
        ctx["trade_result"] = result
        return result