"""
Phase 7: Logging — Registrar todo para análisis y entrenamiento futuro.
"""
from typing import Optional


class PhaseLogging:
    """Registra cada acción en los logs (dashboard + training)"""

    def __init__(self, summary_logger):
        self.summary_logger = summary_logger

    def execute(self, ctx: dict, action: Optional[dict] = None,
                reason: str = "", result: Optional[dict] = None):
        """Genera un log para la acción actual"""
        agent = ctx["agent"]
        symbol = ctx["symbol"]

        conclusion = "HOLD"
        confidence = 0.0
        if action:
            conclusion = action.get("tipo", "HOLD")
            if isinstance(conclusion, int):
                conclusion = {0: "BUY", 1: "SELL"}.get(conclusion, "HOLD")
            confidence = action.get("confidence", 0.0)

        if reason == "ejecutado":
            action_taken = "executed"
        elif reason == "bloqueado IA" or ctx.get("validation", {}).get("blocked"):
            action_taken = "blocked_by_ai"
        else:
            action_taken = "skipped"

        df = ctx.get("df_indicators")
        indicators = {}
        if df is not None and len(df) > 0:
            last = df.iloc[-1]
            for col in df.columns:
                indicators[col] = float(last[col]) if hasattr(last[col], "item") else last[col]

        self.summary_logger.log_analysis(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            symbol=symbol,
            indicators_used=indicators,
            signals_found=[],
            conclusion=conclusion,
            confidence=confidence,
            action_taken=action_taken,
            reason=reason,
            ai_validation=ctx.get("validation"),
            price=action.get("price", 0) if action else 0,
        )

        if result:
            self.summary_logger.log_trade_result(
                agent_id=agent.agent_id,
                agent_name=agent.name,
                symbol=symbol,
                action=action_taken,
                entry_price=result.get("price", 0),
                exit_price=result.get("price", 0),
                profit=result.get("profit", 0),
                profit_pct=0,
                exit_reason=reason,
                duration="",
                analysis_snapshot=ctx.get("validation"),
            )