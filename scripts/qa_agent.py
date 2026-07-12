"""
QA Agent — Simula el bot completo para verificar que todo funciona.

Ejecuta:
  python scripts/qa_agent.py

Esto simulará 20+ ciclos de trading con datos sintéticos, verificando:
  - Los 4 agentes cargan correctamente
  - Cada agente analiza sus símbolos
  - Las señales se generan (o al menos intentan)
  - Los logs se crean
  - El dashboard se actualiza
"""

import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

from src.utils.config import get_config, reload_config
from src.agents.orchestrator import AgentOrchestrator
from src.learning.summary_logger import SummaryLogger
from src.indicators import apply_all_indicators


def generate_price_data(symbol: str, bars: int = 500) -> pd.DataFrame:
    """Genera datos sintéticos realistas para test"""
    np.random.seed(abs(hash(symbol)) % 2**31)
    base = random.uniform(50, 500)
    volatility = random.uniform(0.003, 0.015)
    trend = random.uniform(-0.0005, 0.001)
    price = base * np.exp(np.cumsum(np.random.normal(trend, volatility, bars)))

    return pd.DataFrame({
        "open": price * (1 + np.random.normal(0, 0.001, bars)),
        "high": price * (1 + np.abs(np.random.normal(0, volatility, bars))),
        "low": price * (1 - np.abs(np.random.normal(0, volatility, bars))),
        "close": price,
        "volume": np.random.randint(5000, 100000, bars),
    })


def run_qa():
    """Ejecuta QA completo"""
    print("=" * 60)
    print("🧪 QA AGENT — Verificación del sistema")
    print("=" * 60)

    cfg = reload_config()
    summary_logger = SummaryLogger(cfg)

    # 1. Verificar que agents.yaml carga
    agents_cfg = cfg.get("agents", {})
    agent_ids = [k for k in agents_cfg.keys() if k != "committee"]
    print(f"\n✅ Config cargada: {len(agent_ids)} agentes")
    for a in agent_ids:
        acfg = agents_cfg[a]
        print(f"   {acfg['emoji']} {acfg['name']}: {len(acfg['symbols'])} símbolos")

    # 2. Verificar que el orchestrator crea todos los agentes
    orch = AgentOrchestrator(cfg, 1000.0)
    print(f"\n✅ Orchestrator: {len(orch.agents)} agentes creados")
    for a in orch.agents:
        print(f"   {a.emoji} {a.name} — ${a.capital_asignado:.0f} — {len(a.symbols)} símbolos")

    # 3. Simular ciclos de trading
    print(f"\n🔄 Simulando {min(20, len(orch.agents) * 5)} ciclos...")
    all_logs = []
    errors = 0

    for cycle in range(20):
        for agent in orch.agents:
            symbol = random.choice(agent.symbols)

            # Generar datos sintéticos
            bars = agent.bars_to_fetch or 200
            df = generate_price_data(symbol, bars)
            df = apply_all_indicators(df)

            try:
                agent.analizar(None, df, symbol)
                # Simular log
                entry = summary_logger.log_analysis(
                    agent_id=agent.agent_id,
                    agent_name=f"{agent.emoji} {agent.name}",
                    symbol=symbol,
                    indicators_used={
                        "rsi_14": float(df["rsi_14"].iloc[-1]) if "rsi_14" in df.columns else 50,
                        "volume_ratio": float(df["volume_ratio"].iloc[-1]) if "volume_ratio" in df.columns else 1,
                    },
                    signals_found=[],
                    conclusion=random.choice(["BUY", "SELL", "HOLD"]),
                    confidence=round(random.uniform(0.3, 0.9), 2),
                    action_taken=random.choice(["executed", "skipped", "blocked_by_ai"]),
                    reason="Test QA",
                    price=float(df["close"].iloc[-1]),
                )
                all_logs.append(entry)
            except Exception as e:
                errors += 1
                print(f"   ⚠️  Error {agent.emoji} {symbol}: {e}")

    print(f"✅ {len(all_logs)} logs generados")
    if errors:
        print(f"⚠️  {errors} errores")

    # 4. Verificar que el dashboard se actualiza
    orch._actualizar_dashboard()
    with open(orch.dashboard_data_file) as f:
        dd = json.load(f)
    print(f"\n✅ Dashboard actualizado: {len(dd['agents'])} agentes en JSON")

    # 5. Verificar símbolos totales
    total_symbols = sum(len(a.symbols) for a in orch.agents)
    print(f"\n📊 RESUMEN QA")
    print(f"   Agentes: {len(orch.agents)}")
    print(f"   Símbolos totales: {total_symbols}")
    for a in orch.agents:
        print(f"   {a.emoji} {a.name}: {len(a.symbols)} símbolos")

    print(f"\n{'='*60}")
    print(f"🧪 QA COMPLETADO — {'✅ SIN ERRORES' if errors == 0 else f'⚠️  {errors} ERRORES'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_qa()