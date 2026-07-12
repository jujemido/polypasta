"""
Risk Manager — Gestión de riesgo: sizing, stop-loss, drawdown.

Toda la configuración está en config/risk.yaml.
Cambia ahí, no aquí.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os


class RiskError(Exception):
    pass


class MaxDrawdownExceeded(RiskError):
    pass


class MaxDailyLossExceeded(RiskError):
    pass


class MaxPositionsExceeded(RiskError):
    pass


@dataclass
class TradeResult:
    """Resultado de un trade cerrado"""
    symbol: str
    action: str
    entry_price: float
    exit_price: float
    volume: float
    profit: float
    profit_pct: float
    exit_reason: str  # "take_profit", "stop_loss", "manual", "signal"


class RiskManager:
    """
    Gestor de riesgo centralizado.
    - Calcula tamaño de posición (Kelly / fixed / percent)
    - Controla stop-loss, take-profit
    - Monitorea drawdown
    """

    def __init__(self, config: dict):
        self.cfg = config["risk"]
        self.positions_cfg = self.cfg["positions"]
        self.sl_cfg = self.cfg["stop_loss"]
        self.tp_cfg = self.cfg["take_profit"]
        self.dd_cfg = self.cfg["drawdown"]
        self.method = self.cfg["method"]

        # Estado
        self._initial_balance: float = 0.0
        self._current_balance: float = 0.0
        self._peak_balance: float = 0.0
        self._open_positions: int = 0
        self._daily_trades: int = 0
        self._daily_pnl: float = 0.0
        self._weekly_pnl: float = 0.0
        self._trades_history: list[TradeResult] = []
        self._day_start = datetime.now().date()
        self._week_start = datetime.now().isocalendar()[1]
        self._cooldown_until: Optional[datetime] = None

    def initialize(self, initial_balance: float):
        """Inicializa con el balance de la cuenta"""
        self._initial_balance = initial_balance
        self._current_balance = initial_balance
        self._peak_balance = initial_balance

    # ─────────────────────────────────────────────
    # Sizing
    # ─────────────────────────────────────────────

    def calculate_position_size(
        self,
        price: float,
        balance: Optional[float] = None,
        signal_confidence: float = 1.0,
    ) -> float:
        """
        Calcula el tamaño de posición (en lotes/número de acciones).
        Devuelve 0 si no se puede operar.
        """
        bal = balance or self._current_balance

        if self.method == "fixed":
            amount = self.cfg["fixed"]["amount_per_trade"]
        elif self.method == "percent_equity":
            pct = self.cfg["percent_equity"]["per_trade"]
            max_pct = self.cfg["percent_equity"]["max_per_trade"]
            amount = min(bal * pct, bal * max_pct)
        elif self.method == "kelly_fractional":
            amount = self._kelly_sizing(bal, signal_confidence)
        else:
            amount = bal * 0.25  # Default 25%

        # Convertir a lotes (para CFDs: 1 lote = $1 por punto aprox)
        # Ajustar según el precio del símbolo
        lot_size = round(amount / price, 2)

        # Aplicar límites
        min_lot = self.cfg["fixed"]["amount_per_trade"] / price * 0.5
        max_lot = self.cfg["fixed"]["amount_per_trade"] * 2 / price

        lot_size = max(min_lot, min(lot_size, max_lot))
        lot_size = round(lot_size * 100) / 100  # Redondear a 2 decimales

        return max(lot_size, 0.01)  # Mínimo 0.01 lotes

    def _kelly_sizing(self, balance: float, confidence: float) -> float:
        """Kelly Criterion fraccional"""
        kelly_cfg = self.cfg["kelly"]
        if not kelly_cfg["enabled"]:
            return balance * 0.25

        # Calcular win rate de últimos N trades
        recent = self._trades_history[-kelly_cfg["history_trades"]:]
        if recent:
            wins = sum(1 for t in recent if t.profit > 0)
            win_rate = wins / len(recent)
            avg_win = sum(t.profit for t in recent if t.profit > 0) / max(wins, 1)
            avg_loss = abs(sum(t.profit for t in recent if t.profit <= 0)) / max(len(recent) - wins, 1)
            if avg_loss > 0:
                kelly_pct = win_rate - ((1 - win_rate) / (avg_win / avg_loss))
            else:
                kelly_pct = win_rate
        else:
            kelly_pct = 0.5  # Sin historial, asumir 50%

        # Fraccional
        kelly_pct = max(0, kelly_pct) * kelly_cfg["fraction"] * confidence
        kelly_pct = min(kelly_pct, kelly_cfg["max_kelly_pct"])

        return balance * kelly_pct

    # ─────────────────────────────────────────────
    # Risk Checks
    # ─────────────────────────────────────────────

    def can_trade(self) -> bool:
        """¿Podemos hacer un nuevo trade?"""

        # Cooldown por drawdown
        if self._cooldown_until and datetime.now() < self._cooldown_until:
            remaining = (self._cooldown_until - datetime.now()).seconds // 60
            print(f"⏳ Cooldown active — {remaining} min remaining")
            return False

        # Límite de drawdown diario
        dd = self.get_current_drawdown()
        if dd > self.dd_cfg["max_daily"]:
            print(f"🛑 Daily drawdown exceeded: {dd:.1%} > {self.dd_cfg['max_daily']:.0%}")
            self._cooldown_until = datetime.now() + timedelta(hours=self.dd_cfg["cooldown_hours"])
            return False

        # Límite de drawdown total
        total_dd = self.get_total_drawdown()
        if total_dd > self.dd_cfg["max_total"]:
            print(f"🛑 Total drawdown exceeded: {total_dd:.1%} > {self.dd_cfg['max_total']:.0%}")
            return False

        # Límite de pérdida diaria
        if self._daily_pnl < 0 and abs(self._daily_pnl) > self._current_balance * self.sl_cfg["max_loss_per_day"]:
            print(f"🛑 Daily loss limit hit: {self._daily_pnl:.2f}")
            return False

        # Máximo posiciones
        if self._open_positions >= self.positions_cfg["max_open"]:
            print(f"⛔ Max positions reached: {self._open_positions}")
            return False

        return True

    def check_symbol_limit(self, symbol: str, current_symbols: list) -> bool:
        """¿Podemos añadir este símbolo?"""
        if self.positions_cfg["max_per_symbol"] <= 0:
            return True
        count = sum(1 for s in current_symbols if s == symbol)
        return count < self.positions_cfg["max_per_symbol"]

    # ─────────────────────────────────────────────
    # Stop Loss / Take Profit
    # ─────────────────────────────────────────────

    def calculate_sl(self, entry_price: float, direction: str, atr: float = 0) -> float:
        """Calcula el stop loss"""
        if direction == "buy":
            if atr > 0:
                sl_atr = self.sl_cfg.get("atr_multiplier", 1.5)
                return round(entry_price - atr * sl_atr, 2)
            else:
                sl_pct = self.sl_cfg.get("default_pct", 0.02)
                return round(entry_price * (1 - sl_pct), 2)
        else:  # sell
            if atr > 0:
                sl_atr = self.sl_cfg.get("atr_multiplier", 1.5)
                return round(entry_price + atr * sl_atr, 2)
            else:
                sl_pct = self.sl_cfg.get("default_pct", 0.02)
                return round(entry_price * (1 + sl_pct), 2)

    def calculate_tp(self, entry_price: float, direction: str, atr: float = 0) -> float:
        """Calcula el take profit"""
        if direction == "buy":
            if atr > 0:
                tp_atr = self.tp_cfg.get("atr_multiplier", 3.0)
                return round(entry_price + atr * tp_atr, 2)
            else:
                tp_pct = self.tp_cfg.get("default_pct", 0.04)
                return round(entry_price * (1 + tp_pct), 2)
        else:  # sell
            if atr > 0:
                tp_atr = self.tp_cfg.get("atr_multiplier", 3.0)
                return round(entry_price - atr * tp_atr, 2)
            else:
                tp_pct = self.tp_cfg.get("default_pct", 0.04)
                return round(entry_price * (1 - tp_pct), 2)

    # ─────────────────────────────────────────────
    # State management
    # ─────────────────────────────────────────────

    def on_trade_opened(self):
        """Actualizar estado tras abrir trade"""
        self._open_positions += 1

    def on_trade_closed(self, trade: TradeResult):
        """Actualizar estado tras cerrar trade"""
        self._open_positions = max(0, self._open_positions - 1)
        self._current_balance += trade.profit
        self._peak_balance = max(self._peak_balance, self._current_balance)

        self._daily_trades += 1
        self._daily_pnl += trade.profit
        self._weekly_pnl += trade.profit

        self._trades_history.append(trade)

        # Reset diario si cambia el día
        today = datetime.now().date()
        if today != self._day_start:
            self._day_start = today
            self._daily_trades = 0
            self._daily_pnl = 0.0

        # Reset semanal si cambia la semana
        week = datetime.now().isocalendar()[1]
        if week != self._week_start:
            self._week_start = week
            self._weekly_pnl = 0.0

    # ─────────────────────────────────────────────
    # Metrics
    # ─────────────────────────────────────────────

    def get_current_drawdown(self) -> float:
        """Drawdown actual desde el pico"""
        if self._peak_balance <= 0:
            return 0.0
        return (self._peak_balance - self._current_balance) / self._peak_balance

    def get_total_drawdown(self) -> float:
        """Drawdown total desde el inicio"""
        if self._initial_balance <= 0:
            return 0.0
        return (self._initial_balance - self._current_balance) / self._initial_balance

    def get_win_rate(self) -> float:
        """Win rate de todos los trades"""
        if not self._trades_history:
            return 0.0
        wins = sum(1 for t in self._trades_history if t.profit > 0)
        return wins / len(self._trades_history)

    def get_total_pnl(self) -> float:
        """P&L total"""
        return self._current_balance - self._initial_balance

    def get_metrics(self) -> dict:
        """Todas las métricas en un dict"""
        return {
            "initial_balance": round(self._initial_balance, 2),
            "current_balance": round(self._current_balance, 2),
            "total_pnl": round(self.get_total_pnl(), 2),
            "open_positions": self._open_positions,
            "daily_trades": self._daily_trades,
            "daily_pnl": round(self._daily_pnl, 2),
            "weekly_pnl": round(self._weekly_pnl, 2),
            "current_drawdown": round(self.get_current_drawdown(), 4),
            "total_drawdown": round(self.get_total_drawdown(), 4),
            "win_rate": round(self.get_win_rate(), 4),
            "total_trades": len(self._trades_history),
        }