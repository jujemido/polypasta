"""
Strategy Factory — Crea la estrategia activa según config.

Para añadir una nueva estrategia:
  1. Crea archivo en src/strategies/tu_estrategia.py
  2. Crea la clase heredando de BaseStrategy
  3. Impórtala aquí en STRATEGY_MAP
"""

from typing import Optional
from src.strategies.base import BaseStrategy
from src.strategies.mean_reversion import MeanReversion
from src.strategies.sma_crossover import SMACrossover


# Registry: nombre → clase
STRATEGY_MAP = {
    "mean_reversion": MeanReversion,
    "sma_crossover": SMACrossover,
}


def get_strategy(config: dict, name: Optional[str] = None) -> BaseStrategy:
    """Crea la estrategia activa según config."""
    strategy_name = name or config["strategy"].get("active_strategy", "mean_reversion")

    if strategy_name not in STRATEGY_MAP:
        available = ", ".join(STRATEGY_MAP.keys())
        raise ValueError(
            f"Strategy '{strategy_name}' not found. "
            f"Available: {available}. "
            f"Add it to STRATEGY_MAP in src/strategies/factory.py"
        )

    strategy_class = STRATEGY_MAP[strategy_name]
    strategy = strategy_class(config)

    print(f"📊 Strategy loaded: {strategy}")
    return strategy


def list_strategies() -> list:
    """Lista todas las estrategias disponibles"""
    return list(STRATEGY_MAP.keys())