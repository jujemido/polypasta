"""
Broker Connection — Conexión con MetaTrader 5 vía API Python.

Fácil de cambiar:
  - Cambia broker.yaml → cambia de broker/plataforma
  - Cambia account.type → demo/real
  - Cambia mt5.server → conectas a demo o real
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

# Intentar importar MT5 (puede no estar instalado en desarrollo)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️  MetaTrader5 not installed. Install with: pip install MetaTrader5")


class BrokerNotConnectedError(Exception):
    pass


class Broker:
    """Wrapper sobre MetaTrader 5 para trading algorítmico"""

    def __init__(self, config: dict):
        self.cfg = config["broker"]
        self.mt5_cfg = self.cfg["mt5"]
        self.account_cfg = self.cfg["account"]
        self.limits = self.cfg["limits"]
        self._connected = False
        self._account_info = None

    # ─────────────────────────────────────────────
    # Conexión
    # ─────────────────────────────────────────────

    def connect(self) -> bool:
        """Conecta a MT5. Devuelve True si éxito."""
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package is required. pip install MetaTrader5")

        # Inicializar MT5
        path = self.mt5_cfg["path"] or None
        initialized = mt5.initialize(
            path=path,
            login=self.mt5_cfg["login"] or None,
            password=self.mt5_cfg["password"] or None,
            server=self.mt5_cfg["server"],
            timeout=self.mt5_cfg["timeout"],
        )

        if not initialized:
            error = mt5.last_error()
            print(f"❌ MT5 connection failed: {error}")
            return False

        # Verificar conexión
        self._account_info = mt5.account_info()
        if self._account_info is None:
            print(f"❌ No account info: {mt5.last_error()}")
            mt5.shutdown()
            return False

        self._connected = True
        acct = self._account_info
        print(f"✅ MT5 connected — Server: {self.mt5_cfg['server']}")
        print(f"   Account: {acct.login} | Balance: {acct.balance:.2f} {acct.currency}")
        print(f"   Leverage: 1:{acct.leverage} | Mode: {self.account_cfg['type']}")
        return True

    def disconnect(self):
        """Desconecta de MT5"""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            print("🔌 MT5 disconnected")

    def is_connected(self) -> bool:
        return self._connected

    def check_connection(self):
        """Lanza excepción si no conectado"""
        if not self._connected:
            raise BrokerNotConnectedError("Not connected to MT5. Call connect() first.")

    # ─────────────────────────────────────────────
    # Data
    # ─────────────────────────────────────────────

    def get_rates(
        self,
        symbol: str,
        timeframe: str = "1h",
        bars: int = 200,
        from_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Obtiene velas históricas o en tiempo real"""
        self.check_connection()

        tf_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1,
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)

        if from_date:
            rates = mt5.copy_rates_from(symbol, mt5_tf, from_date, bars)
        else:
            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)

        if rates is None or len(rates) == 0:
            print(f"⚠️  No data for {symbol} ({timeframe})")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)

        # Renombrar columnas para consistencia
        df.rename(columns={
            "tick_volume": "volume",
            "real_volume": "volume_exchange",
        }, inplace=True)

        return df

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Info de un símbolo (spread, punto, mínimo lote, etc.)"""
        self.check_connection()
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return {
            "name": info.name,
            "spread": info.spread,
            "digits": info.digits,
            "point": info.point,
            "trade_mode": info.trade_mode,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "trade_stops_level": info.trade_stops_level,
            "bid": info.bid,
            "ask": info.ask,
        }

    # ─────────────────────────────────────────────
    # Trading
    # ─────────────────────────────────────────────

    def get_positions(self) -> List[Dict[str, Any]]:
        """Lista de posiciones abiertas"""
        self.check_connection()
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "buy" if p.type == 0 else "sell",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "swap": p.swap,
                "comment": p.comment,
                "open_time": datetime.fromtimestamp(p.time),
            }
            for p in positions
        ]

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        """Posición abierta para un símbolo específico"""
        self.check_connection()
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return None
        p = positions[0]
        return {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "buy" if p.type == 0 else "sell",
            "volume": p.volume,
            "price_open": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
        }

    def has_open_position(self, symbol: str) -> bool:
        """Hay posición abierta en este símbolo?"""
        return self.get_position_by_symbol(symbol) is not None

    def open_trade(
        self,
        symbol: str,
        order_type: str,  # "buy" | "sell"
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: str = "PolypastaBot",
        magic: int = 202507,
    ) -> Optional[int]:
        """Abre una orden de mercado. Devuelve ticket o None."""
        self.check_connection()

        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"❌ Symbol {symbol} not found")
            return None

        # Asegurar que el símbolo está habilitado
        if not info.trade_mode == 0:  # SYMBOL_TRADE_MODE_FULL
            mt5.symbol_select(symbol, True)

        point = info.point
        digits = info.digits

        order = mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if order_type == "buy" else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order,
            "price": price,
            "sl": float(sl) if sl else 0.0,
            "tp": float(tp) if tp else 0.0,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ {order_type.upper()} {symbol} vol={volume} @ {price:.{digits}f} → ticket #{result.order}")
            return result.order
        else:
            error_code = result.retcode if result else "N/A"
            print(f"❌ Trade failed ({symbol}): code {error_code}")
            return None

    def close_trade(self, ticket: int, comment: str = "Polypasta Close") -> bool:
        """Cierra una posición por ticket"""
        self.check_connection()

        position = mt5.positions_get(ticket=ticket)
        if not position:
            print(f"⚠️  Position #{ticket} not found")
            return False

        pos = position[0]
        order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(pos.symbol).bid if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 10,
            "magic": 202507,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        success = result and result.retcode == mt5.TRADE_RETCODE_DONE
        if success:
            print(f"✅ Closed #{ticket} {pos.symbol} — Profit: {pos.profit:.2f}")
        else:
            print(f"❌ Close failed #{ticket}: code {result.retcode if result else 'N/A'}")
        return success

    def close_all_positions(self) -> int:
        """Cierra todas las posiciones. Devuelve número cerradas."""
        positions = self.get_positions()
        count = 0
        for pos in positions:
            if self.close_trade(pos["ticket"]):
                count += 1
        return count

    # ─────────────────────────────────────────────
    # Account
    # ─────────────────────────────────────────────

    def get_balance(self) -> float:
        """Balance actual de la cuenta"""
        if not self._connected:
            return 0.0
        info = mt5.account_info()
        if info:
            self._account_info = info
            return info.balance
        return self._account_info.balance if self._account_info else 0.0

    def get_equity(self) -> float:
        """Equity actual (balance + P&L no realizado)"""
        if not self._connected:
            return 0.0
        info = mt5.account_info()
        if info:
            return info.equity
        return 0.0

    def get_account_summary(self) -> dict:
        """Resumen completo de la cuenta"""
        if not self._connected:
            return {"connected": False}
        info = mt5.account_info()
        if not info:
            return {"connected": False}
        return {
            "connected": True,
            "login": info.login,
            "server": info.server,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "margin_free": info.margin_free,
            "margin_level": info.margin_level,
            "profit": info.profit,
            "leverage": info.leverage,
            "currency": info.currency,
        }


def create_broker(config: dict) -> Broker:
    """Factory: crea y conecta el broker"""
    broker = Broker(config)
    return broker