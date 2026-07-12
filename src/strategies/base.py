"""
Base Strategy — Clase base para todas las estrategias.

Cada estrategia hereda de aquí y solo implementa:
  - calculate_signals(df) → pd.Series con señales (1=buy, -1=sell, 0=nada)
  - PROPERTIES: name, description, config_section

Así añadir una nueva estrategia es crear 1 archivo con 1 clase.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime


class Signal:
    """Señal de trading generada por una estrategia"""

    def __init__(
        self,
        symbol: str,
        action: str,  # "buy" | "sell" | "close_long" | "close_short" | "none"
        confidence: float = 1.0,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        reason: str = "",
        metadata: Optional[Dict] = None,
    ):
        self.symbol = symbol
        self.action = action
        self.confidence = confidence
        self.price = price
        self.sl = sl
        self.tp = tp
        self.reason = reason
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def is_valid(self) -> bool:
        """Señal válida y ejecutable"""
        return self.action != "none" and self.confidence > 0.3

    def __repr__(self):
        return f"[{self.timestamp:%H:%M}] {self.action.upper():<12} {self.symbol} | conf={self.confidence:.2f} | {self.reason}"


class BaseStrategy(ABC):
    """
    Clase base para estrategias de trading.
    Hereda y define:
      - name: str
      - description: str
      - config_section: str (clave en strategy.yaml)
      - calculate_signals(df) → list[Signal]
    """

    name: str = "base"
    description: str = "Base strategy"
    config_section: str = ""  # Clave en strategy.yaml

    def __init__(self, config: dict):
        self.cfg = config["strategy"]
        self.risk_cfg = config["risk"]
        self.strategy_params = self._load_params()
        self.symbols = []
        self.last_signals = []

    def _load_params(self) -> dict:
        """Carga parámetros específicos de esta estrategia desde YAML"""
        if self.config_section and self.config_section in self.cfg:
            return self.cfg[self.config_section]
        return {}

    def configure(self, symbols: list[str]):
        """Configura los símbolos a operar"""
        self.symbols = symbols

    @abstractmethod
    def calculate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """
        Calcula señales para un símbolo dado su DataFrame de velas.
        Devuelve lista de Signal (normalmente 0 o 1).
        """
        pass

    def get_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Obtiene la señal más fuerte (si hay varias)"""
        signals = self.calculate_signals(df, symbol)
        self.last_signals = signals
        valid_signals = [s for s in signals if s.is_valid()]
        if not valid_signals:
            return None
        # Devolver la de mayor confianza
        return max(valid_signals, key=lambda s: s.confidence)

    def get_params(self) -> dict:
        """Parámetros actuales (para logging/optimización)"""
        return dict(self.strategy_params)

    def __repr__(self):
        return f"{self.name}: {self.description}"