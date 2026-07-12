"""
Phase 1: Data — Obtener velas del mercado del broker.
"""
import pandas as pd
from typing import Optional


class PhaseData:
    """Obtiene datos de mercado del broker (sandbox o real)"""

    def __init__(self, broker, config: dict):
        self.broker = broker
        self.config = config

    def execute(self, ctx: dict) -> Optional[pd.DataFrame]:
        """Obtiene velas para el símbolo"""
        symbol = ctx["symbol"]
        timeframe = ctx["timeframe"]
        agent = ctx["agent"]

        bars = getattr(agent, "bars_to_fetch", 200)
        df = self.broker.get_rates(symbol, timeframe, bars)

        if df is None or df.empty:
            return None

        ctx["df_raw"] = df
        return df