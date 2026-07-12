"""
Backtest Engine — Simula trades con datos históricos para evaluar estrategias.

Uso:
    python -m src.utils.backtest

O desde el engine:
    run.py --backtest
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

from src.utils.config import get_config
from src.strategies.factory import get_strategy
from src.indicators import apply_all_indicators


def run_backtest(config: dict, strategy=None, risk_manager=None) -> Dict[str, Any]:
    """
    Ejecuta un backtest completo de la estrategia activa.

    Args:
        config: Config del proyecto
        strategy: Estrategia a testear (o None = usar activa)
        risk_manager: RiskManager (o None = crear uno nuevo)

    Returns:
        Dict con métricas: win_rate, sharpe, max_dd, total_pnl, trades
    """
    from src.risk.manager import RiskManager

    cfg = config
    strategy_params = cfg["strategy"]
    strategy_name = cfg["strategy"]["active_strategy"]

    if strategy is None:
        strategy = get_strategy(cfg)

    risk = risk_manager or RiskManager(cfg)
    risk.initialize(config["broker"]["account"]["initial_balance"])

    # Determinar timeframe y barras
    timeframe = getattr(strategy.strategy_params, "get", lambda k, d: d)("timeframe", "1h")
    bars = getattr(strategy.strategy_params, "get", lambda k, d: d)("bars_to_fetch", 500)

    # Símbolos a testear
    symbols = cfg["broker"]["limits"]["allowed_symbols"]

    print(f"\n📊 Backtesting {strategy.name}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Symbols: {', '.join(symbols[:3])}...")
    print(f"   Initial balance: ${risk._initial_balance:.2f}")

    all_trades = []

    for symbol in symbols[:3]:  # Limitar a 3 símbolos para backtest rápido
        print(f"\n   Testing {symbol}...")
        trades = _backtest_symbol(
            symbol=symbol,
            strategy=strategy,
            risk=risk,
            timeframe=timeframe,
            bars=bars,
            config=cfg,
        )
        all_trades.extend(trades)

    # Métricas
    metrics = risk.get_metrics()
    metrics["total_trades"] = len(all_trades)
    metrics["symbols_tested"] = len(symbols[:3])

    if all_trades:
        profits = [t.get("profit", 0) for t in all_trades if t.get("profit") is not None]
        if profits:
            metrics["avg_profit"] = round(np.mean(profits), 2)
            metrics["max_profit"] = round(max(profits), 2)
            metrics["max_loss"] = round(min(profits), 2)
            metrics["profit_factor"] = round(
                sum(p for p in profits if p > 0) / max(abs(sum(p for p in profits if p < 0)), 0.01),
                2,
            )
            metrics["std_profit"] = round(np.std(profits), 2)
            if metrics["std_profit"] > 0:
                metrics["sharpe_ratio"] = round(
                    (metrics["avg_profit"] / metrics["std_profit"]) * np.sqrt(252),
                    2,
                )
            else:
                metrics["sharpe_ratio"] = 0

    # Log
    from src.utils.file_utils import log_performance
    log_performance(cfg["paths"]["performance_log"], metrics)

    print(f"\n   ✅ Backtest complete — {len(all_trades)} trades")
    return metrics


def _backtest_symbol(
    symbol: str,
    strategy,
    risk,
    timeframe: str = "1h",
    bars: int = 500,
    config: Optional[dict] = None,
) -> List[Dict]:
    """
    Backtest para un símbolo específico.

    Simula el comportamiento del bot barra por barra.
    """
    # Para backtest sin broker, generamos datos mock
    # En producción usarías datos reales de MT5/históricos
    print(f"      Generating synthetic data for {symbol}...")

    # Generar datos sintéticos (para demo)
    np.random.seed(42)
    periods = min(bars, 1000)
    dates = pd.date_range(
        end=datetime.now(),
        periods=periods,
        freq=timeframe.upper().replace("H", "h"),
    )

    # Random walk con mean reversion
    returns = np.random.normal(0.0001, 0.005, periods)
    price = 100 * np.exp(np.cumsum(returns))
    volatility = np.random.uniform(0.002, 0.01, periods)

    df = pd.DataFrame({
        "time": dates,
        "open": price * (1 + np.random.normal(0, 0.001, periods)),
        "high": price * (1 + np.abs(np.random.normal(0, 0.005, periods))),
        "low": price * (1 - np.abs(np.random.normal(0, 0.005, periods))),
        "close": price,
        "volume": np.random.randint(1000, 100000, periods),
    })

    # Aplicar indicadores
    df = apply_all_indicators(df)

    trades = []
    has_position = False
    entry_price = 0
    entry_time = None
    position_type = None

    # Simular barra por barra
    for i in range(max(50, len(df) - 50)):
        if i + 50 >= len(df):
            break

        window = df.iloc[:i + 50]
        current = df.iloc[i + 50]

        if not has_position:
            # Buscar señal de entrada
            signal = strategy.get_signal(window, symbol)
            if signal and signal.is_valid():
                has_position = True
                entry_price = current["close"]
                entry_time = current["time"]
                position_type = signal.action

                trades.append({
                    "timestamp": str(current["time"]),
                    "symbol": symbol,
                    "action": signal.action,
                    "volume": 0.01,
                    "entry_price": entry_price,
                    "profit": 0,
                    "exit_price": 0,
                    "status": "open",
                    "reason": signal.reason,
                })
        else:
            # Buscar señal de salida
            signal = strategy.get_signal(window, symbol)
            should_close = False
            exit_reason = "signal"

            if signal and signal.action != position_type:
                should_close = True

            # Stop-loss / take-profit simulados
            change = (current["close"] - entry_price) / entry_price
            if position_type == "sell":
                change = -change

            if change < -0.02:
                should_close = True
                exit_reason = "stop_loss"
            elif change > 0.04:
                should_close = True
                exit_reason = "take_profit"

            if should_close:
                exit_price = current["close"]
                profit = (exit_price - entry_price) * 100 if position_type == "buy" else (entry_price - exit_price) * 100
                # Aproximar comisiones
                profit -= 0.1  # ~$0.1 comisión

                # Actualizar último trade
                trades[-1]["exit_price"] = exit_price
                trades[-1]["profit"] = round(profit, 2)
                trades[-1]["exit_reason"] = exit_reason
                trades[-1]["status"] = "closed"

                has_position = False

    return trades