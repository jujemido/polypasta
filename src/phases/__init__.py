"""
Pipeline — Ejecuta las fases del bot en orden secuencial.

Cada fase es un archivo independiente en src/phases/.
El Pipeline las ejecuta en orden, pasando el contexto de una a otra.

Fases:
  1. Data   → Obtener velas del mercado
  2. Indicators → Calcular indicadores técnicos
  3. Signals → Generar señales de trading
  4. Validation → AI Validator (opcional)
  5. Risk   → Risk management (Kelly, drawdown, SL/TP)
  6. Execution → Ejecutar trades
  7. Logging → Registrar todo
  8. Dashboard → Actualizar el dashboard
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from src.phases.phase_01_data import PhaseData
from src.phases.phase_02_indicators import PhaseIndicators
from src.phases.phase_03_signals import PhaseSignals
from src.phases.phase_04_validation import PhaseValidation
from src.phases.phase_05_risk import PhaseRisk
from src.phases.phase_06_execution import PhaseExecution
from src.phases.phase_07_logging import PhaseLogging
from src.phases.phase_08_dashboard import PhaseDashboard


class Pipeline:
    """
    Pipeline de trading. Ejecuta las 8 fases en orden para cada
    combinación agente × símbolo.
    """

    def __init__(self, config: dict, agents: list, broker, ai_validator, summary_logger):
        self.config = config
        self.agents = agents
        self.broker = broker
        self.ai_validator = ai_validator
        self.summary_logger = summary_logger

        # Instanciar fases
        self.phases = {
            "data": PhaseData(broker, config),
            "indicators": PhaseIndicators(),
            "signals": PhaseSignals(config),
            "validation": PhaseValidation(ai_validator),
            "risk": PhaseRisk(config),
            "execution": PhaseExecution(broker, config),
            "logging": PhaseLogging(summary_logger),
            "dashboard": PhaseDashboard(config),
        }

    def run(self, agents: Optional[List] = None) -> Dict:
        """
        Ejecuta el pipeline completo para todos los agentes/símbolos.

        Returns:
            Dict con resultados del ciclo
        """
        cycle_start = datetime.now()
        results = {"cycle_start": cycle_start.isoformat(), "actions": [], "errors": []}

        for agent in agents or self.agents:
            if getattr(agent, "_is_treasury", False):
                continue

            for symbol in agent.symbols:
                ctx = {"agent": agent, "symbol": symbol, "timeframe": agent.timeframe}

                try:
                    # 1. Data
                    df = self.phases["data"].execute(ctx)
                    if df is None:
                        continue

                    # 2. Indicators
                    df = self.phases["indicators"].execute(ctx, df)
                    if df is None:
                        continue

                    # 3. Signals
                    action = self.phases["signals"].execute(ctx, df)
                    if action is None:
                        self.phases["logging"].execute(ctx, action=None, reason="sin señal")
                        continue

                    # 4. Validation (AI)
                    decision = self.phases["validation"].execute(ctx, action)
                    if decision.get("blocked"):
                        self.phases["logging"].execute(ctx, action, reason=decision.get("reason", "bloqueado IA"))
                        results["actions"].append({"symbol": symbol, "action": "blocked", "reason": decision.get("reason")})
                        continue

                    # 5. Risk
                    risk_result = self.phases["risk"].execute(ctx, action)
                    if risk_result is None:
                        self.phases["logging"].execute(ctx, action, reason="riesgo denegado")
                        continue

                    # 6. Execution
                    trade_result = self.phases["execution"].execute(ctx, risk_result)
                    if trade_result:
                        # 7. Logging
                        self.phases["logging"].execute(ctx, action, reason="ejecutado", result=trade_result)
                        results["actions"].append({"symbol": symbol, "action": "executed", "result": trade_result})

                        # Treasury: skim 20% of profit
                        treasury = next((a for a in self.agents if getattr(a, "_is_treasury", False)), None)
                        if treasury and hasattr(treasury, "process_profit"):
                            profit = trade_result.get("profit", 0)
                            if profit > 0:
                                treasury.process_profit(agent.name, symbol, profit)

                except Exception as e:
                    results["errors"].append({"symbol": symbol, "agent": agent.name, "error": str(e)})
                    print(f"  ❌ {agent.emoji} {agent.name}/{symbol}: {e}")

        # 8. Dashboard
        self.phases["dashboard"].execute(results, self.agents)

        # Summary
        print(f"  ─────────────────────────────")
        print(f"  📊 Pipeline completado — {len(results['actions'])} acciones, {len(results['errors'])} errores")
        return results