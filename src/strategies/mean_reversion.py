"""
Mean Reversion Strategy — Bollinger Bands + RSI.

Compra cuando precio toca banda inferior + RSI sobrevendido.
Vende cuando precio toca banda superior + RSI sobrecomprado.
"""

import pandas as pd
import numpy as np
from typing import List, Optional

from src.strategies.base import BaseStrategy, Signal
from src.indicators import RSI, BollingerBands, ATR, VolumeSMA


class MeanReversion(BaseStrategy):
    """Mean reversion usando Bollinger Bands + RSI + filtro de volumen"""

    name = "mean_reversion"
    description = "Bollinger Bands + RSI Mean Reversion"
    config_section = "mean_reversion"

    def calculate_signals(self, df: pd.DataFrame, symbol: str) -> List[Signal]:
        params = self.strategy_params

        # Parámetros desde YAML
        bb_period = params.get("bollinger", {}).get("period", 20)
        bb_std = params.get("bollinger", {}).get("std_dev", 2.0)
        bb_std_entry = params.get("bollinger", {}).get("std_dev_entry", 2.0)
        rsi_period = params.get("rsi", {}).get("period", 14)
        rsi_oversold = params.get("rsi", {}).get("oversold", 30)
        rsi_overbought = params.get("rsi", {}).get("overbought", 70)
        volume_enabled = params.get("volume", {}).get("enabled", False)
        volume_min_ratio = params.get("volume", {}).get("min_ratio", 1.2)
        confirmation_candles = params.get("entry", {}).get("long_confirmation", 0)

        if df.empty or len(df) < max(bb_period, rsi_period) + 5:
            return []

        # Calcular indicadores
        bb = BollingerBands(df, bb_period, bb_std)
        rsi = RSI(df, rsi_period)
        atr = ATR(df, 14)
        vol_sma = VolumeSMA(df)

        df = df.copy()
        df["bb_lower"] = bb["bb_lower"]
        df["bb_upper"] = bb["bb_upper"]
        df["bb_middle"] = bb["bb_middle"]
        df["rsi"] = rsi
        df["atr"] = atr
        df["vol_sma"] = vol_sma
        df["vol_ratio"] = df["volume"] / vol_sma

        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        signals = []

        # --- LONG signal ---
        long_condition = (
            last["close"] <= last["bb_lower"]
            and last["rsi"] < rsi_oversold
        )

        if volume_enabled:
            long_condition = long_condition and (last["vol_ratio"] > volume_min_ratio)

        if long_condition:
            sl_pct = self.risk_cfg.get("stop_loss", {}).get("default_pct", 0.02)
            tp_pct = self.risk_cfg.get("take_profit", {}).get("default_pct", 0.04)

            price = last["close"]
            sl = price * (1 - sl_pct)
            tp = price * (1 + tp_pct)

            confidence = min(1.0, (rsi_oversold - last["rsi"]) / rsi_oversold + 0.5)
            confidence = max(0.3, min(1.0, confidence))

            signals.append(Signal(
                symbol=symbol,
                action="buy",
                confidence=round(confidence, 2),
                price=price,
                sl=round(sl, 2),
                tp=round(tp, 2),
                reason=f"MeanRev LONG | RSI={last['rsi']:.0f} | BB%={last.get('bb_percent_b', 0):.2f}",
            ))

        # --- SHORT signal ---
        short_condition = (
            last["close"] >= last["bb_upper"]
            and last["rsi"] > rsi_overbought
        )

        if volume_enabled:
            short_condition = short_condition and (last["vol_ratio"] > volume_min_ratio)

        if short_condition:
            sl_pct = self.risk_cfg.get("stop_loss", {}).get("default_pct", 0.02)
            tp_pct = self.risk_cfg.get("take_profit", {}).get("default_pct", 0.04)

            price = last["close"]
            sl = price * (1 + sl_pct)
            tp = price * (1 - tp_pct)

            confidence = min(1.0, (last["rsi"] - rsi_overbought) / (100 - rsi_overbought) + 0.5)
            confidence = max(0.3, min(1.0, confidence))

            signals.append(Signal(
                symbol=symbol,
                action="sell",
                confidence=round(confidence, 2),
                price=price,
                sl=round(sl, 2),
                tp=round(tp, 2),
                reason=f"MeanRev SHORT | RSI={last['rsi']:.0f} | BB%={last.get('bb_percent_b', 0):.2f}",
            ))

        return signals