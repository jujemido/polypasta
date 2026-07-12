"""
Base Agent — Clase base para todos los agentes de trading.

Cada agente hereda de aquí y define:
  - Su personalidad (nombre, emoji, descripción)
  - Su estrategia (implementar analizar())
  - Su gestión de riesgo (SL/TP propios)
  - Sus mercados y timeframe

El agente gestiona SU PROPIO capital de forma independiente.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

from src.risk.manager import RiskManager, TradeResult
from src.utils.file_utils import log_trade, log_performance, ensure_dir


class AgentAction:
    """Acción que un agente quiere ejecutar"""

    def __init__(
        self,
        symbol: str,
        action: str,  # "buy" | "sell" | "close" | "hold"
        confidence: float = 0.0,
        volume: float = 0.0,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        reason: str = "",
    ):
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.volume = volume
        self.price = price
        self.sl = sl
        self.tp = tp
        self.reason = reason
        self.timestamp = datetime.now()
        self.agent_name = ""

    def is_valid(self) -> bool:
        return self.action in ("buy", "sell") and self.confidence > 0.3 and self.volume > 0

    def __repr__(self):
        icon = "🟢" if self.action == "buy" else "🔴" if self.action == "sell" else "⚪"
        return f"{icon} [{self.agent_name}] {self.action.upper()} {self.symbol} conf={self.confidence:.2f} vol={self.volume} | {self.reason}"


class BaseAgent(ABC):
    """
    Clase base para agentes de trading.

    Propiedades que cada agente define:
      agent_id: str          — "conservative", "aggressive", etc.
      name: str              — "Conservador", etc.
      emoji: str             — "🤵", etc.
      description: str       — Una línea

    Método a implementar:
      analizar(self, broker) → Optional[AgentAction]
    """

    agent_id: str = "base"
    name: str = "Base"
    emoji: str = "🤖"
    description: str = "Agente base"

    def __init__(self, config: dict, agent_cfg: dict, total_balance: float):
        """
        Args:
            config: Config global del proyecto
            agent_cfg: Config específica de este agente (de agents.yaml)
            total_balance: Balance total de la cuenta para calcular su %
        """
        self.cfg = config
        self.agent_cfg = agent_cfg
        self.strategy_cfg = agent_cfg.get("strategy", {})
        self.risk_cfg = agent_cfg.get("risk", {})

        # Capital asignado a este agente
        self.capital_pct = agent_cfg.get("capital_pct", 0.25)
        self.capital_asignado = total_balance * self.capital_pct
        self.balance_inicial = self.capital_asignado
        self.balance_actual = self.capital_asignado

        # Símbolos y timeframe
        self.symbols = agent_cfg.get("symbols", [])
        self.timeframe = agent_cfg.get("timeframe", "1h")
        self.bars_to_fetch = agent_cfg.get("bars_to_fetch", 200)
        self.max_positions = agent_cfg.get("max_positions", 2)

        # Risk manager propio
        self.risk = RiskManager(config)
        self.risk.initialize(self.capital_asignado)

        # Logging propio
        self._trades_file = f"data/logs/agent_{self.agent_id}.csv"
        self._perf_file = f"data/logs/agent_{self.agent_id}_perf.json"

        # Estado
        self._last_action: Optional[AgentAction] = None
        self._total_trades = 0
        self._win_trades = 0

    # ─────────────────────────────────────────────
    # Método principal que cada agente implementa
    # ─────────────────────────────────────────────

    @abstractmethod
    def analizar(self, broker, df: pd.DataFrame, symbol: str) -> Optional[AgentAction]:
        """
        Analiza el mercado y decide si comprar/vender.

        Args:
            broker: Conexión al broker MT5
            df: DataFrame con velas + indicadores
            symbol: Símbolo que se está analizando

        Returns:
            AgentAction o None si no hace nada
        """
        pass

    # ─────────────────────────────────────────────
    # Ciclo de vida
    # ─────────────────────────────────────────────

    def ejecutar_ciclo(self, broker) -> Optional[AgentAction]:
        """
        Un ciclo completo del agente:
        1. Verificar posiciones abiertas
        2. Obtener datos
        3. Analizar
        4. Si hay señal y riesgo lo permite → ejecutar

        Returns:
            AgentAction ejecutado, o None
        """
        # Verificar si podemos operar
        if not self.risk.can_trade():
            return None

        # Obtener posiciones actuales de ESTE agente
        open_positions = self._get_open_positions(broker)
        open_symbols = [p["symbol"] for p in open_positions]
        self.risk._open_positions = len(open_positions)

        if len(open_positions) >= self.max_positions:
            return None

        # Analizar cada símbolo
        for symbol in self.symbols:
            # Saltar si ya tenemos posición en este símbolo
            if symbol in open_symbols:
                continue

            # Fetch data
            df = broker.get_rates(symbol, self.timeframe, self.bars_to_fetch)
            if df.empty or len(df) < 50:
                continue

            # Aplicar indicadores
            from src.indicators import apply_all_indicators
            df = apply_all_indicators(df)

            # Analizar
            action = self.analizar(broker, df, symbol)
            if action and action.is_valid():
                return action

        return None

    def _get_open_positions(self, broker) -> List[Dict]:
        """Obtiene posiciones abiertas, filtradas por símbolos de este agente"""
        all_positions = broker.get_positions()
        return [p for p in all_positions if p["symbol"] in self.symbols]

    # ─────────────────────────────────────────────
    # Ejecución de trades
    # ─────────────────────────────────────────────

    def ejecutar_action(self, broker, action: AgentAction):
        """Ejecuta la acción decidida por el agente"""
        action.agent_name = f"{self.emoji} {self.name}"

        # Calcular volumen basado en SU capital
        volumen = self.risk.calculate_position_size(
            price=action.price or 0,
            balance=self.balance_actual,
            signal_confidence=action.confidence,
        )
        if volumen <= 0:
            return None

        action.volume = volumen

        # Ejecutar
        ticket = broker.open_trade(
            symbol=action.symbol,
            order_type=action.action,
            volume=volumen,
            sl=action.sl,
            tp=action.tp,
            comment=f"Polypasta_{self.agent_id}",
        )

        if ticket:
            self.risk.on_trade_opened()
            self._last_action = action
            self._log_trade(action, ticket)
            self.balance_actual -= action.price * volumen * 0.001  # Aprox comisión

        return ticket

    def _log_trade(self, action: AgentAction, ticket: int):
        """Log del trade a CSV propio"""
        trade_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id,
            "symbol": action.symbol,
            "action": action.action,
            "volume": action.volume,
            "price": action.price,
            "sl": action.sl,
            "tp": action.tp,
            "confidence": action.confidence,
            "reason": action.reason,
            "ticket": ticket,
            "balance_after": self.balance_actual,
        }
        log_trade(self._trades_file, trade_data)

    def on_trade_closed(self, symbol: str, profit: float):
        """Cuando un trade de este agente se cierra (desde el engine)"""
        self.balance_actual += profit
        self.risk.on_trade_closed(TradeResult(
            symbol=symbol,
            action="",
            entry_price=0,
            exit_price=0,
            volume=0,
            profit=profit,
            profit_pct=profit / self.balance_actual if self.balance_actual > 0 else 0,
            exit_reason="",
        ))
        if profit > 0:
            self._win_trades += 1
        self._total_trades += 1

        # Log performance
        log_performance(self._perf_file, self.get_metrics())

    # ─────────────────────────────────────────────
    # Métricas
    # ─────────────────────────────────────────────

    def get_metrics(self) -> Dict[str, Any]:
        """Métricas de este agente"""
        return {
            "agent_id": self.agent_id,
            "name": f"{self.emoji} {self.name}",
            "capital_pct": self.capital_pct,
            "capital_inicial": round(self.balance_inicial, 2),
            "balance_actual": round(self.balance_actual, 2),
            "pnl": round(self.balance_actual - self.balance_inicial, 2),
            "pnl_pct": round((self.balance_actual - self.balance_inicial) / max(self.balance_inicial, 0.01) * 100, 2),
            "win_rate": round(self.risk.get_win_rate(), 2),
            "total_trades": self._total_trades,
            "drawdown": round(self.risk.get_current_drawdown(), 4),
            "open_positions": self.risk._open_positions,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "risk_stars": self.agent_cfg.get("risk_stars", 3),
            "target_win_rate": self.agent_cfg.get("target_win_rate", 0.5),
            "status": "activo" if self.risk.can_trade() else "cooldown",
        }

    def summary_line(self) -> str:
        """Resumen de una línea para Telegram"""
        m = self.get_metrics()
        pnl_icon = "📈" if m["pnl"] >= 0 else "📉"
        return (
            f"{self.emoji} <b>{self.name}</b> ({self.capital_pct:.0%}): "
            f"${m['balance_actual']:.2f} {pnl_icon} {m['pnl']:+.2f} ({m['pnl_pct']:+.1f}%) "
            f"| {m['total_trades']} trades | WR: {m['win_rate']:.0%}"
        )

    def __repr__(self):
        return f"{self.emoji} {self.name} ({self.capital_pct:.0%} · {self.timeframe})"