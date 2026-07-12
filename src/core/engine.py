"""
Trading Engine — Bucle principal de trading.

Soporta dos modos:
  - SINGLE: Una estrategia (modo clásico)
  - MULTI: Múltiples agentes con capital independiente

Ahora por defecto usa AgentOrchestrator para multi-agente.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import os

from src.core.broker import Broker
from src.core.sandbox_broker import SandboxBroker, create_sandbox_broker
from src.strategies.factory import get_strategy
from src.agents.orchestrator import AgentOrchestrator
from src.risk.manager import RiskManager
from src.notifier.telegram import TelegramNotifier
from src.utils.file_utils import log_error, read_trades
from src.utils.time_utils import timeframe_to_minutes


class TradingEngine:
    """Motor principal de trading multi-agente"""

    def __init__(self, config: dict, multi_agent: bool = True):
        self.cfg = config
        self.mode = config["broker"]["account"]["type"]
        self.multi_agent = multi_agent

        # Componentes compartidos
        broker_name = config["broker"]["name"]
        if broker_name == "sandbox":
            self.broker = create_sandbox_broker(config)
            print("🏖️  SANDBOX MODE — Datos reales de Yahoo Finance, trades simulados")
        else:
            self.broker = Broker(config)
        self.notifier = TelegramNotifier(config)

        # Agent Orchestrator (multi-agente)
        self.orchestrator: Optional[AgentOrchestrator] = None

        # Legacy single-strategy (para compatibilidad)
        self.strategy = None
        self.risk = None

        # Estado
        self._running = False
        self._errors_path = config["paths"]["errors_log"]

    # ─────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────

    def startup(self):
        """Inicializa todos los componentes"""
        print(f"\n{'='*50}")
        print(f"🚀 PolypastaBot — {self.mode.upper()} MODE")
        print(f"{'='*50}\n")

        if not self.broker.connect():
            raise ConnectionError("Failed to connect to broker")

        balance = self.broker.get_balance()

        if self.multi_agent:
            self._startup_multi(balance)
        else:
            self._startup_single(balance)

    def _startup_multi(self, balance: float):
        """Inicializa modo multi-agente"""
        print(f"🧠 MODO MULTI-AGENTE\n")
        self.orchestrator = AgentOrchestrator(self.cfg, balance)

        print(f"\n📋 Agentes cargados:")
        for a in self.orchestrator.agents:
            print(f"   {a.emoji} {a.name} — ${a.capital_asignado:.2f} ({a.capital_pct:.0%})")
            print(f"      Mercados: {', '.join(a.symbols[:3])}")
            print(f"      Timeframe: {a.timeframe}")
            print(f"      SL: {a.risk_cfg.get('stop_loss_pct', 0)*100:.1f}% | TP: {(a.risk_cfg.get('take_profit_pct') or 0)*100:.1f}%")

        total_asignado = sum(a.capital_asignado for a in self.orchestrator.agents)
        print(f"\n💰 Capital total: ${balance:.2f} → Asignado: ${total_asignado:.2f}")

        if abs(total_asignado - balance) > 0.01:
            print(f"⚠️  Diferencia: ${balance - total_asignado:.2f} no asignado")
        print()

        self.notifier.send_message(self.orchestrator.get_summary_text())

    def _startup_single(self, balance: float):
        """Inicializa modo single-strategy (legacy)"""
        print(f"📋 MODO SINGLE-STRATEGY\n")
        self.strategy = get_strategy(self.cfg)
        self.risk = RiskManager(self.cfg)
        self.risk.initialize(balance)
        self.strategy.configure(self.cfg["broker"]["limits"]["allowed_symbols"])
        print(f"📊 Strategy: {self.strategy.name}")
        print(f"💰 Balance: ${balance:.2f}\n")
        self.notifier.notify_startup(self.mode, self.strategy.name)

    def shutdown(self):
        """Cierra todo ordenadamente"""
        print("\n🛑 Shutting down...")
        self._running = False
        self.broker.disconnect()
        print("👋 Bye!")

    # ─────────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────────

    def run_once(self) -> List[Dict]:
        """Un ciclo de trading"""
        if self.multi_agent:
            return self._run_once_multi()
        return self._run_once_single()

    def _run_once_multi(self) -> List[Dict]:
        """Ciclo multi-agente: el orquestador ejecuta a todos"""
        acciones = self.orchestrator.ejecutar_ciclo(self.broker)

        # Si hubo acciones, notificar
        if acciones:
            for acc in acciones:
                self.notifier.send_message(
                    f"{acc.agent_name}: {acc.action.upper()} {acc.symbol} @ {acc.price}"
                )
            # Resumen
            self.notifier.send_message(self.orchestrator.get_summary_text())

        # Generar dashboard data (ya lo hace el orquestador)
        return [vars(a) for a in acciones]

    def _run_once_single(self) -> List[Dict]:
        """Ciclo single-strategy (legacy, simplificado)"""
        # Mantenido por compatibilidad pero la funcionalidad
        # completa está en la versión anterior del engine
        return []

    def run_loop(self, interval_minutes: int = 15):
        """
        Bucle infinito que ejecuta todos los agentes cada N minutos.

        En multi-agente cada agente opera en su propio timeframe,
        pero el orquestador revisa cada N minutos por nuevas velas.

        Args:
            interval_minutes: Intervalo entre ciclos (default 15 para multi-agente)
        """
        self._running = True
        print(f"🔄 Running cycle every {interval_minutes} min...\n")

        while self._running:
            cycle_start = time.time()

            try:
                trades = self.run_once()
            except Exception as e:
                log_error(self._errors_path, f"Cycle error: {e}")
                print(f"❌ Cycle error: {e}")
                trades = []

            # Esperar hasta el próximo ciclo
            elapsed = time.time() - cycle_start
            sleep_time = max(0, interval_minutes * 60 - elapsed)
            next_time_ts = datetime.now().timestamp() + sleep_time

            print(f"💤 Next cycle at {datetime.fromtimestamp(next_time_ts):%H:%M:%S} "
                  f"(in {sleep_time/60:.0f} min)")

            try:
                time.sleep(sleep_time)
            except KeyboardInterrupt:
                print("\n⏹️  Interrupted by user")
                break

        self.shutdown()

    # ─────────────────────────────────────────────
    # Entry points
    # ─────────────────────────────────────────────

    def run(self, interval_minutes: int = 15):
        """Ejecuta el bot en el modo configurado"""
        self.startup()

        if self.mode == "demo":
            print("\n📋 DEMO MODE — No real money\n")
        else:
            print("\n💰 REAL MONEY MODE\n")

        self.run_loop(interval_minutes)

    def run_backtest(self):
        """Ejecuta backtest en modo single (legacy)"""
        print("\n📊 BACKTEST — solo disponible en modo single")
        print("   Para multi-agente, ejecuta primero en demo\n")
        self._startup_single(self.broker.get_balance())
        from src.utils.backtest import run_backtest
        results = run_backtest(self.cfg, self.strategy, self.risk)
        self.shutdown()
        return results