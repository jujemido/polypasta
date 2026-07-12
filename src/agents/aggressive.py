"""
Aggressive Agent — Maximiza rentabilidad con alta volatilidad en USA.

Personalidad: "El que pega primero, pega dos veces. Prefiero perder
               una oportunidad que entrar tarde."

Mercados: NASDAQ, S&P 500, Russell 2000
Timeframe: 15m
Capital: 35%
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.agents.base import BaseAgent, AgentAction
from src.indicators import RSI, BollingerBands, VolumeSMA, ATR


class AggressiveAgent(BaseAgent):
    agent_id = "aggressive"
    name = "Agresivo"
    emoji = "🏃"
    description = "Maximiza rentabilidad aceptando alta volatilidad en USA"

    def analizar(self, broker, df: pd.DataFrame, symbol: str) -> Optional[AgentAction]:
        s = self.strategy_cfg
        rsi_p = s.get("rsi_period", 14)
        rsi_os = s.get("rsi_oversold", 25)
        rsi_ob = s.get("rsi_overbought", 75)
        bb_period = s.get("bb_period", 20)
        bb_std = s.get("bb_std", 2.0)
        vol_min = s.get("volume_min_ratio", 1.2)
        mom_min = s.get("momentum_min", 0.15)

        if len(df) < max(bb_period, rsi_p) + 5:
            return None

        # Indicadores
        rsi = RSI(df, rsi_p)
        bb = BollingerBands(df, bb_period, bb_std)
        vol_sma = VolumeSMA(df)
        vol_ratio = df["volume"] / vol_sma
        atr = ATR(df, 14)

        price = df["close"].iloc[-1]
        prev_price = df["close"].iloc[-2]
        momentum_pct = (price - prev_price) / prev_price * 100

        # ─── LONG: RSI sobreventa + tocó banda inferior + volumen ───
        if price <= bb["bb_lower"].iloc[-1] and rsi.iloc[-1] < rsi_os:
            confianza = 0.5 + (rsi_os - rsi.iloc[-1]) / 100

            if vol_ratio.iloc[-1] > vol_min:
                confianza += 0.15

            # Si ya está rebotando (momentum positivo), más confianza
            if momentum_pct > 0:
                confianza += 0.1

            confianza = min(confianza, 0.95)

            sl_pct = self.risk_cfg.get("stop_loss_pct", 0.015)
            tp_pct = self.risk_cfg.get("take_profit_pct", 0.03)

            return AgentAction(
                symbol=symbol,
                action="buy",
                confidence=round(confianza, 2),
                price=price,
                sl=round(price * (1 - sl_pct), 2),
                tp=round(price * (1 + tp_pct), 2),
                reason=f"🔥 RSI={rsi.iloc[-1]:.0f} extremo + BB touch + vol x{vol_ratio.iloc[-1]:.1f}",
            )

        # ─── SHORT: RSI sobrecompra + tocó banda superior ───
        if price >= bb["bb_upper"].iloc[-1] and rsi.iloc[-1] > rsi_ob:
            confianza = 0.5 + (rsi.iloc[-1] - rsi_ob) / 100

            if vol_ratio.iloc[-1] > vol_min:
                confianza += 0.15
            if momentum_pct < 0:
                confianza += 0.1

            confianza = min(confianza, 0.95)

            sl_pct = self.risk_cfg.get("stop_loss_pct", 0.015)
            tp_pct = self.risk_cfg.get("take_profit_pct", 0.03)

            return AgentAction(
                symbol=symbol,
                action="sell",
                confidence=round(confianza, 2),
                price=price,
                sl=round(price * (1 + sl_pct), 2),
                tp=round(price * (1 - tp_pct), 2),
                reason=f"🔥 RSI={rsi.iloc[-1]:.0f} sobrecompra + BB touch",
            )

        # ─── MOMENTUM: subida fuerte con volumen (entrada rápida) ───
        if momentum_pct > mom_min and vol_ratio.iloc[-1] > 2.0 and rsi.iloc[-1] < 60:
            sl_pct = self.risk_cfg.get("stop_loss_pct", 0.015)
            tp_pct = self.risk_cfg.get("take_profit_pct", 0.03)

            return AgentAction(
                symbol=symbol,
                action="buy",
                confidence=0.6,
                price=price,
                sl=round(price * (1 - sl_pct), 2),
                tp=round(price * (1 + tp_pct), 2),
                reason=f"⚡ Momentum {momentum_pct:.2f}% + vol x{vol_ratio.iloc[-1]:.1f}",
            )

        return None