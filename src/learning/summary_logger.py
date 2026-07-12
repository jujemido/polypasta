"""
Summary Logger — Crea logs detallados de cada operación para:
  1. Dashboard en tiempo real
  2. Análisis posterior (qué funcionó, qué no)
  3. Entrenamiento futuro del bot

Cada vez que un agente analiza un símbolo y decide algo (comprar, vender,
o no hacer nada), se genera un log. Si la IA bloquea la operación,
también se genera un log con el motivo del bloqueo.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any


class SummaryLogger:
    """
    Logger detallado de operaciones de agentes.

    Genera dos tipos de logs:
      1. agent_logs → para el dashboard (últimas N entradas)
      2. training_logs → para entrenamiento futuro (completo, detallado)
    """

    def __init__(self, config: dict):
        lcfg = config.get("learning", {}).get("summary_logger", {})
        self.enabled = lcfg.get("enabled", True)
        self.max_entries = lcfg.get("max_entries", 1000)
        self.detail_level = lcfg.get("detail_level", "high")
        self.save_for_training = lcfg.get("save_for_training", True)
        self.training_dir = lcfg.get("training_data_path", "data/logs/training/")

        self._logs: List[Dict] = []

        if self.save_for_training:
            os.makedirs(self.training_dir, exist_ok=True)

    # ─────────────────────────────────────────────
    # Log de análisis completo de un agente
    # ─────────────────────────────────────────────

    def log_analysis(
        self,
        agent_id: str,
        agent_name: str,
        symbol: str,
        indicators_used: Dict[str, Any],
        signals_found: List[Dict],
        conclusion: str,  # "BUY" | "SELL" | "HOLD"
        confidence: float,
        action_taken: str,  # "executed" | "blocked_by_ai" | "skipped"
        reason: str,
        ai_validation: Optional[Dict] = None,
        price: float = 0.0,
    ) -> Dict:
        """
        Crea un log detallado de un ciclo de análisis.

        Returns:
            Dict con el log (también añadido a la lista interna)
        """
        timestamp = datetime.now().isoformat()

        # Indicadores resumidos para el dashboard
        ind_summary = self._summarize_indicators(indicators_used)

        # Log para dashboard (compacto)
        dashboard_entry = {
            "timestamp": timestamp,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "symbol": symbol,
            "indicators": ind_summary,
            "conclusion": conclusion,
            "confidence": round(confidence, 2),
            "action": action_taken,
            "reason": reason,
            "price": round(price, 2) if price else 0,
        }
        self._logs.append(dashboard_entry)

        # Limitar tamaño
        if len(self._logs) > self.max_entries:
            self._logs = self._logs[-self.max_entries:]

        # Log detallado para entrenamiento (JSON completo)
        if self.save_for_training and self.detail_level == "high":
            training_entry = {
                "timestamp": timestamp,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "symbol": symbol,
                "price": round(price, 2) if price else 0,
                "indicators_full": indicators_used,
                "signals": signals_found,
                "conclusion": conclusion,
                "confidence": confidence,
                "action_taken": action_taken,
                "reason": reason,
                "ai_validation": ai_validation,
            }
            self._save_training_log(training_entry)

        return dashboard_entry

    # ─────────────────────────────────────────────
    # Log de operación completada (éxito/fracaso)
    # ─────────────────────────────────────────────

    def log_trade_result(
        self,
        agent_id: str,
        agent_name: str,
        symbol: str,
        action: str,
        entry_price: float,
        exit_price: float,
        profit: float,
        profit_pct: float,
        exit_reason: str,
        duration: str,
        analysis_snapshot: Optional[Dict] = None,
    ) -> Dict:
        """
        Crea un log detallado del resultado de un trade cerrado.
        Esto es lo que se usará para mejorar el bot en el futuro.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "trade_result",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "symbol": symbol,
            "action": action,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 4),
            "exit_reason": exit_reason,
            "duration": duration,
            "success": profit > 0,
            "analysis_at_entry": analysis_snapshot,
        }

        if self.save_for_training:
            self._save_training_log(entry, prefix="trade_result")

        return entry

    # ─────────────────────────────────────────────
    # Log de bloqueo por IA
    # ─────────────────────────────────────────────

    def log_blocked(
        self,
        agent_id: str,
        agent_name: str,
        symbol: str,
        action_requested: str,
        agent_confidence: float,
        agent_reason: str,
        ai_decision: Dict,
    ) -> Dict:
        """
        Log cuando la IA bloquea una operación.
        Especialmente útil para depurar y mejorar el bot.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "blocked_by_ai",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "symbol": symbol,
            "action_requested": action_requested,
            "agent_confidence": agent_confidence,
            "agent_reason": agent_reason,
            "ai_decision": ai_decision.get("decision", "block"),
            "ai_confidence": ai_decision.get("confidence", 0),
            "ai_reason": ai_decision.get("reason", ""),
        }
        self._logs.append(entry)

        if self.save_for_training:
            self._save_training_log(entry, prefix="blocked")

        return entry

    # ─────────────────────────────────────────────
    # Getters
    # ─────────────────────────────────────────────

    def get_recent_logs(self, limit: int = 200) -> List[Dict]:
        """Últimos logs para el dashboard"""
        return self._logs[-limit:]

    def get_logs_by_agent(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Logs filtrados por agente"""
        return [l for l in self._logs if l.get("agent_id") == agent_id][-limit:]

    # ─────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────

    def _summarize_indicators(self, indicators: Dict) -> str:
        """Resume los indicadores en una línea para el dashboard"""
        if not indicators:
            return ""
        # Coger los más relevantes
        parts = []
        for key in ["rsi_14", "sma_20", "sma_50", "bb_position", "volume_ratio", "atr_14"]:
            if key in indicators:
                val = indicators[key]
                if isinstance(val, float):
                    parts.append(f"{key}={val:.1f}")
                else:
                    parts.append(f"{key}={val}")
        return ", ".join(parts[:10]) or str(indicators)[:100]

    def _save_training_log(self, entry: Dict, prefix: str = "analysis"):
        """Guarda un log JSON para entrenamiento futuro"""
        date_str = datetime.now().strftime("%Y%m")
        filename = f"{self.training_dir}{prefix}_{date_str}.jsonl"
        try:
            with open(filename, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            print(f"⚠️  Training log error: {e}")