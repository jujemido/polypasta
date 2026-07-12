"""
Phase 2: Live Trading — Bot en modo real con 50€.

Ejecutar:
    python phases/live_trade.py

REQUISITOS ANTES DE EJECUTAR:
  1️⃣ Ejecutar Phase 1 (paper) durante 2+ semanas
  2️⃣ Tener win rate > 40% en paper
  3️⃣ Depositar USDT en Exness (cuenta REAL)
  4️⃣ Cambiar en config/broker.yaml:
       account.type: real
       mt5.server: "Exness-MT5Real"
       mt5.login: <tu_login_real>
  5️⃣ Establecer stop-loss máximo en risk.yaml
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config import get_config
from src.core.engine import TradingEngine


def run_live_phase():
    """
    Fase 2 — Live Trading real con capital gestionado.

    Capital: 50€ (depositado en Exness vía USDT)
    Apalancamiento: 1:5 (configurable en broker.yaml)
    Risk: Kelly fraccional 25%, stop-loss 2%, max drawdown 20%

    Monitoreo:
    - Notificaciones Telegram en cada trade
    - Dashboard web en data/dashboard.html
    - Logs de trades en data/logs/trades.csv
    """
    print("=" * 60)
    print("💰 PHASE 2: LIVE TRADING")
    print("   Capital real — 50€")
    print("=" * 60)
    print()
    print("⚠️  ¡ATENCIÓN! Estás ejecutando en MODO REAL.")
    print("   Asegúrate de haber completado Phase 1 primero.")
    print()

    confirm = input("¿Continuar con LIVE TRADING? (escribe 'LIVE' para confirmar): ")
    if confirm != "LIVE":
        print("❌ Cancelado.")
        return

    cfg = get_config()

    if cfg["broker"]["account"]["type"] != "real":
        print("❌ Account type must be 'real' in config/broker.yaml")
        print("   Cambia account.type: real y mt5.server al servidor real")
        return

    engine = TradingEngine(cfg)
    engine.run_live(interval_minutes=120)


if __name__ == "__main__":
    run_live_phase()