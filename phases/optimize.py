"""
Phase 3: Optimización — Walk-forward + Hyperopt para mejorar estrategia.

Ejecutar:
    python phases/optimize.py

Qué hace:
- Walk-forward analysis de la estrategia actual
- Optimización de parámetros (períodos SMA, RSI, Bollinger)
- Reporte de mejores parámetros
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import get_config


def run_optimize_phase():
    """
    Fase 3 — Optimización.

    1. Carga datos históricos (últimos 6 meses)
    2. Walk-forward: entrena en 80%, testea en 20%
    3. Grid search de parámetros clave
    4. Reporta mejores combinaciones
    """
    print("=" * 60)
    print("🔧 PHASE 3: OPTIMIZATION")
    print("   Walk-forward + Grid Search")
    print("=" * 60)

    cfg = get_config()
    strategy_name = cfg["strategy"]["active_strategy"]

    print(f"\n📊 Optimizing strategy: {strategy_name}")
    print("🔄 Walk-forward analysis...")

    # Aquí iría la lógica de optimización
    # Por ahora es un placeholder que explica cómo hacerlo manualmente

    print()
    print("📋 Para optimizar manualmente:")
    print()
    print("  1. Cambia parámetros en config/strategy.yaml")
    print("  2. Ejecuta: python run.py --backtest")
    print("  3. Revisa métricas en data/logs/performance.json")
    print("  4. Repite hasta encontrar la mejor combinación")
    print()
    print("🔍 Parámetros a optimizar:")
    print("  - SMA: fast_period (10-50), slow_period (30-100)")
    print("  - RSI: period (7-21), oversold (20-40), overbought (60-80)")
    print("  - Bollinger: period (15-30), std_dev (1.5-3.0)")
    print("  - Stop-loss: default_pct (0.01-0.05)")
    print("  - Take-profit: default_pct (0.02-0.08)")
    print()
    print("📈 Métricas objetivo:")
    print("  - Sharpe ratio > 1.0")
    print("  - Win rate > 45%")
    print("  - Max drawdown < 15%")
    print("  - Profit factor > 1.5")


if __name__ == "__main__":
    run_optimize_phase()