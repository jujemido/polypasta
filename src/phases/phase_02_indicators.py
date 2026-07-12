"""
Phase 2: Indicators — Calcular indicadores técnicos sobre las velas.
"""
import pandas as pd
from typing import Optional
from src.indicators import apply_all_indicators


class PhaseIndicators:
    """Calcula indicadores técnicos (RSI, SMA, Bollinger, MACD, ATR, volumen)"""

    def execute(self, ctx: dict, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Aplica indicadores al DataFrame de velas"""
        if df is None or df.empty:
            return None

        df = apply_all_indicators(df)
        ctx["df_indicators"] = df
        return df