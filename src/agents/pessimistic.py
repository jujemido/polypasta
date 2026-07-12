"""
Pessimistic Agent — Busca refugio en incertidumbre. Solo cuando TODO está a favor.

Personalidad: "El mercado siempre encuentra la manera de joderte.
               Voy a estresar esta señal hasta que me demuestre que es segura."

Mercados: Oro, VIX, Nikkei, USD, Bonos
Timeframe: 1h
Capital: 20%
"""

from typing import Optional
import pandas as pd
import numpy as np

from src.agents.base import BaseAgent, AgentAction
from src.indicators import SMA, RSI, MACD, VolumeSMA


class PessimisticAgent(BaseAgent):
    agent_id = "pessimistic"
    name = "Pesimista"
    emoji = "🧐"
    description = "Busca refugio en incertidumbre. Solo cuando todo está a favor."

    def analizar(self, broker, df: pd.DataFrame, symbol: str) -> Optional[AgentAction]:
        s = self.strategy_cfg
        rsi_p = s.get("rsi_period", 14)
        rsi_safe_min = s.get("rsi_safe_min", 40)
        rsi_safe_max = s.get("rsi_safe_max", 60)
        trend_min = s.get("min_trend_strength", 0.2)
        vix_max = s.get("vix_max", 25)
        vol_max_ratio = s.get("volume_max_ratio", 0.8)
        base_pess = self.risk_cfg.get("base_pessimism", 0.15)

        if len(df) < 50:
            return None

        # Indicadores
        sma_200 = SMA(df, 200)
        rsi_vals = RSI(df, rsi_p)
        macd = MACD(df)
        vol_sma = VolumeSMA(df)
        vol_ratio = df["volume"] / vol_sma

        price = df["close"].iloc[-1]
        last = df.iloc[-1]

        # ─── STRESS TEST: buscar razones para NO operar ───
        riesgos = base_pess  # Penalización base por pesimista
        advertencias = []

        # 1. ¿Tendencia general alcista?
        if len(sma_200) > 200:
            tendencia = sma_200.iloc[-1] > sma_200.iloc[-20]
            if not tendencia:
                riesgos += 0.2
                advertencias.append("SMA200 bajista")

        # 2. ¿Precio en zona de soporte?
        soporte_cerca = price <= sma_200.iloc[-1] * 1.05 if len(sma_200) > 200 else False
        if not soporte_cerca:
            riesgos += 0.15
            advertencias.append("Fuera de soporte")

        # 3. ¿RSI en zona segura (ni sobrecompra ni sobreventa)?
        rsi_actual = rsi_vals.iloc[-1]
        if rsi_actual < rsi_safe_min or rsi_actual > rsi_safe_max:
            riesgos += 0.2
            advertencias.append(f"RSI={rsi_actual:.0f} fuera de zona segura")

        # 4. ¿Volumen normal (nada de picos raros)?
        if vol_ratio.iloc[-1] > 1 / vol_max_ratio:
            riesgos += 0.2
            advertencias.append(f"Volumen anormal: x{vol_ratio.iloc[-1]:.1f}")

        # 5. ¿MACD indica tendencia clara?
        macd_hist = macd["macd_hist"].iloc[-1]
        if abs(macd_hist) < trend_min:
            riesgos += 0.15
            advertencias.append("MACD sin tendencia clara")

        # Si hay demasiados riesgos, no operar
        if riesgos > 0.5:
            return None

        # ─── Si pasa todos los filtros, COMPRAR ───
        confianza = max(0.5, 0.9 - riesgos)
        sl_pct = self.risk_cfg.get("stop_loss_pct", 0.02)
        tp_pct = self.risk_cfg.get("take_profit_pct", 0.05)

        advertencias_str = " | ".join(advertencias) if advertencias else "todo OK ✅"

        return AgentAction(
            symbol=symbol,
            action="buy",
            confidence=round(confianza, 2),
            price=price,
            sl=round(price * (1 - sl_pct), 2),
            tp=round(price * (1 + tp_pct), 2),
            reason=f"🛡️ Soportó stress test ({riesgos:.2f}) | {advertencias_str}",
        )