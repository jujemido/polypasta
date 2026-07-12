"""
Long Term Agent — Acumula patrimonio con tendencias de largo recorrido.

Personalidad: "No me importa lo que pase hoy. Dentro de 6 meses esto valdrá más."

Mercados: AAPL, GOOGL, MSFT, SP500, IBEX35
Timeframe: 1d
Capital: 20%
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.agents.base import BaseAgent, AgentAction
from src.indicators import SMA, RSI, MACD


class LongTermAgent(BaseAgent):
    agent_id = "long_term"
    name = "Largo Plazo"
    emoji = "🐢"
    description = "Acumula patrimonio con tendencias de largo recorrido"

    def analizar(self, broker, df: pd.DataFrame, symbol: str) -> Optional[AgentAction]:
        s = self.strategy_cfg
        sma_200_p = s.get("sma_200_period", 200)
        macd_fast = s.get("macd_fast", 12)
        macd_slow = s.get("macd_slow", 26)
        macd_sig = s.get("macd_signal", 9)
        rsi_w_p = s.get("rsi_weekly_period", 14)
        rsi_max = s.get("rsi_max", 60)
        soporte_tol = s.get("soporte_tolerance", 0.05)

        if len(df) < sma_200_p + 20:
            return None

        # Indicadores
        sma_200 = SMA(df, sma_200_p)
        rsi_vals = RSI(df, rsi_w_p)
        macd = MACD(df, macd_fast, macd_slow, macd_sig)

        price = df["close"].iloc[-1]
        last = df.iloc[-1]

        # ─── SEÑAL DE COMPRA: cerca de SMA200 + MACD alcista + RSI no sobrecomp ───
        if price <= sma_200.iloc[-1] * (1 + soporte_tol):
            # MACD mensual alcista (macd > signal)
            if macd["macd"].iloc[-1] > macd["macd_signal"].iloc[-1]:
                if rsi_vals.iloc[-1] < rsi_max:
                    sl_pct = self.risk_cfg.get("stop_loss_pct", 0.10)

                    return AgentAction(
                        symbol=symbol,
                        action="buy",
                        confidence=0.7,
                        price=price,
                        sl=round(price * (1 - sl_pct), 2),
                        tp=None,  # Sin TP fijo
                        reason=f"🐢 Soporte SMA200 + MACD alcista + RSI semanal {rsi_vals.iloc[-1]:.0f}",
                    )

        # ─── SEÑAL DE VENTA: MACD semanal bajista ───
        # Solo si tenemos posición (el engine checkea esto)
        if macd["macd"].iloc[-1] < macd["macd_signal"].iloc[-1]:
            if macd["macd_hist"].iloc[-1] < 0 and macd["macd_hist"].iloc[-2] >= 0:
                # Cruce a bajista
                return AgentAction(
                    symbol=symbol,
                    action="sell",
                    confidence=0.6,
                    price=price,
                    sl=None,
                    tp=None,
                    reason="🐢 MACD semanal giró a bajista — recoger beneficios",
                )

        return None