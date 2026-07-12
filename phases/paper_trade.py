"""
Phase 1: Paper Trading — Bot en modo simulación.

Ejecutar:
    python run.py --paper

O desde este script:
    python phases/paper_trade.py

Configuración en config/broker.yaml -> account.type: demo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import get_config
from src.core.engine import TradingEngine


def run_paper_phase():
    """
    Fase 1 — Paper Trading.

    Qué hace:
    - Conecta a MT5 demo
    - Evalúa estrategia cada 5 minutos
    - NO ejecuta trades reales (demo account)
    - Notifica señales por Telegram
    - Genera dashboard HTML

    Cuándo parar:
    - Después de 50+ trades simulados con win rate > 40%
    - Después de 2+ semanas sin errores de conexión
    """
    print("=" * 60)
    print("📋 PHASE 1: PAPER TRADING")
    print("   Simulación completa sin arriesgar capital real")
    print("=" * 60)

    cfg = get_config()

    # Forzar modo demo
    cfg["broker"]["account"]["type"] = "demo"

    engine = TradingEngine(cfg)
    engine.run_paper()


if __name__ == "__main__":
    run_paper_phase()