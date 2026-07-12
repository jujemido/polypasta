"""
Trading Engine — Bucle principal que usa el Pipeline de fases.
"""

from typing import Optional
from datetime import datetime
import time
import os

from src.core.sandbox_broker import create_sandbox_broker
from src.agents.orchestrator import AgentOrchestrator
from src.utils.file_utils import log_error


class TradingEngine:
    """Motor principal de trading — usa Pipeline de 8 fases"""

    def __init__(self, config: dict):
        self.cfg = config
        self.broker = create_sandbox_broker(config)
        self.orchestrator: Optional[AgentOrchestrator] = None
        self._running = False
        print("🏖️  SANDBOX MODE — Datos reales de Yahoo Finance, trades simulados")

    def startup(self):
        """Inicializa y conecta todo"""
        if not self.broker.connect():
            raise ConnectionError("No se pudo conectar al broker")
        balance = self.broker.get_balance()
        print(f"\n{'='*50}")
        print(f"🚀 PolypastaBot — SANDBOX")
        print(f"{'='*50}\n")
        self.orchestrator = AgentOrchestrator(self.cfg, balance)
        self.orchestrator.pipeline.phases["data"].broker = self.broker
        print(f"\n💰 Balance simulado: ${balance:.2f}\n")

    def shutdown(self):
        """Cierra todo"""
        print("\n🛑 Shutting down...")
        self._running = False
        self.broker.disconnect()
        print("👋 Bye!")

    def run_once(self):
        """Un ciclo de trading usando el Pipeline"""
        return self.orchestrator.ejecutar_ciclo(self.broker)

    def run(self, interval_minutes: int = 15):
        """Bucle infinito con intervalos"""
        self.startup()
        self._running = True
        print(f"🔄 Running cycle every {interval_minutes} min...\n")
        while self._running:
            start = time.time()
            try:
                self.run_once()
            except Exception as e:
                log_error("data/logs/errors.log", f"Cycle: {e}")
                print(f"❌ Cycle error: {e}")
            elapsed = time.time() - start
            sleep = max(0, interval_minutes * 60 - elapsed)
            next_time = datetime.now().timestamp() + sleep
            print(f"💤 Next cycle at {datetime.fromtimestamp(next_time):%H:%M:%S} "
                  f"(in {sleep/60:.0f} min)")
            try:
                time.sleep(sleep)
            except KeyboardInterrupt:
                break
        self.shutdown()