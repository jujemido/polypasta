"""
SMA Crossover Strategy — Cruce de medias móviles con filtro RSI.

Compra cuando SMA rápida cruza arriba SMA lenta + RSI no sobrecompra.
Vende cuando SMA rápida cruza abajo SMA lenta + RSI no sobreventa.
"""

import pandas as pd
import numpy as np
from typing import List, Optional

from src.strategies.base import BaseStrategy, Signal
from src.indicators import SMA, RSI, ATR, VolumeSMA


class SMACrossover(BaseStrategy):
    """Estrategia de cruce de SMA 20/50 con filtros"""

    name = "sma_crossover"
    description = "SMA Crossover 20/50 + RSI filter"
    config_section = "sma_crossover"

    def calculate_signals(self, df: pd.DataFrame, symbol: str) -> List[Signal]:
        params = self.strategy_params

        fast_period = params.get("sma", {}).get("fast_period", 20)
        slow_period = params.get("sma", {}).get("slow_period", 50)
        rsi_period = params.get("rsi_filter", {}).get("period", 14)
        rsi_oversold = params.get("rsi_filter", {}).get("oversold", 30)
        rsi_overbought = params.get("rsi_filter", {}).get("overbought", 70)
        volume_enabled = params.get("volume_filter", {}).get("enabled", False)
        volume_min_ratio = params.get("volume_filter", {}).get("min_ratio", 1.2)
        sl_atr = params.get("exit", {}).get("stop_loss_atr", 1.5)
        tp_atr = params.get("exit", {}).get("take_profit_atr", 3.0)

        if df.empty or len(df) < slow_period + 5:
            return []

        # Calcular indicadores
        sma_fast = SMA(df, fast_period)
        sma_slow = SMA(df, slow_period)
        rsi_vals = RSI(df, rsi_period)
        atr = ATR(df, 14)
        vol_sma = VolumeSMA(df)

        df = df.copy()
        df["sma_fast"] = sma_fast
        df["sma_slow"] = sma_slow
        df["rsi"] = rsi_vals
        df["atr"] = atr
        df["vol_ratio"] = df["volume"] / vol_sma

        # Cruz: comparar última vela vs anterior
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        signals = []

        # --- LONG signal: fast cruza ARRIBA slow ---
        if (
            prev["sma_fast"] <= prev["sma_slow"]
            and last["sma_fast"] > last["sma_slow"]
            and last["rsi"] < rsi_overbought  # no sobrecompra
        ):
            if not volume_enabled or last["vol_ratio"] > volume_min_ratio:
                atr_val = last["atr"]
                sl = last["close"] - atr_val * sl_atr
                tp = last["close"] + atr_val * tp_atr

                confidence = min(1.0, 0.6 + (last["rsi"] / 100) * 0.3)
                signals.append(Signal(
                    symbol=symbol,
                    action="buy",
                    confidence=round(confidence, 2),
                    price=last["close"],
                    sl=round(sl, 2),
                    tp=round(tp, 2),
                    reason=f"SMA Cross LONG | SMA{fast_period}>{slow_period} | RSI={last['rsi']:.0f}",
                ))

        # --- SHORT signal: fast cruza ABAJO slow ---
        if (
            prev["sma_fast"] >= prev["sma_slow"]
            and last["sma_fast"] < last["sma_slow"]
            and last["rsi"] > rsi_oversold  # no sobreventa
        ):
            if not volume_enabled or last["vol_ratio"] > volume_min_ratio:
                atr_val = last["atr"]
                sl = last["close"] + atr_val * sl_atr
                tp = last["close"] - atr_val * tp_atr

                confidence = min(1.0, 0.6 + ((100 - last["rsi"]) / 100) * 0.3)
                signals.append(Signal(
                    symbol=symbol,
                    action="sell",
                    confidence=round(confidence, 2),
                    price=last["close"],
                    sl=round(sl, 2),
                    tp=round(tp, 2),
                    reason=f"SMA Cross SHORT | SMA{fast_period}<{slow_period} | RSI={last['rsi']:.0f}",
                ))

        return signals