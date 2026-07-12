"""
Conservative Agent — Busca movimientos de alta probabilidad en mercados europeos.

Personalidad: "Solo actúo con datos confirmados. Necesito 2 velas, volumen alto,
               y RSI en zona lógica. No me gusta el ruido."

Mercados: IBEX35, DAX, EuroStoxx
Timeframe: 1h
Capital: 25%
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.agents.base import BaseAgent, AgentAction
from src.indicators import SMA, RSI, VolumeSMA


class ConservativeAgent(BaseAgent):
    agent_id = "conservative"
    name = "Conservador"
    emoji = "🤵"
    description = "Busca movimientos de alta probabilidad en mercados europeos"

    def analizar(self, broker, df: pd.DataFrame, symbol: str) -> Optional[AgentAction]:
        s = self.strategy_cfg
        fast = s.get("sma_fast", 20)
        slow = s.get("sma_slow", 50)
        conf_candles = s.get("confirmation_candles", 2)
        vol_min = s.get("volume_min_ratio", 1.3)
        rsi_p = s.get("rsi_period", 14)
        rsi_min = s.get("rsi_min", 40)
        rsi_max = s.get("rsi_max", 70)

        if len(df) < slow + 5:
            return None

        # Calcular indicadores
        sma_fast = SMA(df, fast)
        sma_slow = SMA(df, slow)
        rsi = RSI(df, rsi_p)
        vol_sma = VolumeSMA(df)
        vol_ratio = df["volume"] / vol_sma

        last = df.iloc[-1]
        prev = df.iloc[-2]
        pprev = df.iloc[-3] if len(df) > 2 else prev

        # CHECK LONG: SMA fast CRUZA ARRIBA slow
        # Requiere conf_candles velas de confirmación

        # Detectar cruce
        cruce_arriba = (
            prev["close"] <= sma_slow.iloc[-2]
            and last["close"] > sma_slow.iloc[-1]
        )

        # Confirmación: la vela anterior también tuvo cruce?
        confirmacion = (
            pprev["close"] <= sma_slow.iloc[-3]
            and prev["close"] > sma_slow.iloc[-2]
        ) if conf_candles > 1 else True

        if cruce_arriba and confirmacion:
            # RSI en zona lógica
            if rsi_min <= rsi.iloc[-1] <= rsi_max:
                # Volumen alto
                if vol_ratio.iloc[-1] > vol_min:
                    # Calcular SL/TP
                    sl_pct = self.risk_cfg.get("stop_loss_pct", 0.025)
                    tp_pct = self.risk_cfg.get("take_profit_pct", 0.05)
                    price = last["close"]

                    confianza = 0.6 + min(0.2, (vol_ratio.iloc[-1] - vol_min) * 0.3)
                    return AgentAction(
                        symbol=symbol,
                        action="buy",
                        confidence=round(min(confianza, 0.9), 2),
                        price=price,
                        sl=round(price * (1 - sl_pct), 2),
                        tp=round(price * (1 + tp_pct), 2),
                        reason=f"SMA {fast}/{slow} cruzó + confirmado + RSI ok + vol x{vol_ratio.iloc[-1]:.1f}",
                    )

        # CHECK SHORT: SMA fast CRUZA ABAJO slow
        cruce_abajo = (
            prev["close"] >= sma_slow.iloc[-2]
            and last["close"] < sma_slow.iloc[-1]
        )
        confirmacion_abajo = (
            pprev["close"] >= sma_slow.iloc[-3]
            and prev["close"] < sma_slow.iloc[-2]
        ) if conf_candles > 1 else True

        if cruce_abajo and confirmacion_abajo:
            if rsi_min <= rsi.iloc[-1] <= rsi_max:
                if vol_ratio.iloc[-1] > vol_min:
                    sl_pct = self.risk_cfg.get("stop_loss_pct", 0.025)
                    tp_pct = self.risk_cfg.get("take_profit_pct", 0.05)
                    price = last["close"]

                    return AgentAction(
                        symbol=symbol,
                        action="sell",
                        confidence=0.7,
                        price=price,
                        sl=round(price * (1 + sl_pct), 2),
                        tp=round(price * (1 - tp_pct), 2),
                        reason=f"SMA {fast}/{slow} cruzó abajo + confirmado + volumen",
                    )

        return None