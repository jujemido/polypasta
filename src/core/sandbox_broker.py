"""
Sandbox Broker — Usa Yahoo Finance (GRATIS) para datos reales de mercado.
No necesitas MT5, ni broker, ni nada. Simula trades sobre datos reales.

Para usar: cambia en config/broker.yaml:
  broker:
    name: "sandbox"
    platform: "sandbox"

Así el bot funciona con datos REALES pero sin arriesgar dinero.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import time as _time

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# Mapeo de nuestros símbolos a tickers de Yahoo Finance
SYMBOL_MAP = {
    # ── Índices ──
    "US100": "^IXIC", "US500": "^GSPC", "US30": "^DJI", "US2000": "^RUT",
    "VIX": "^VIX", "IBEX35": "^IBEX", "DAX40": "^GDAXI", "GER40": "^GDAXI",
    "EUROSTOXX50": "^STOXX50E", "UK100": "^FTSE", "CAC40": "^FCHI",
    "FTSE100": "^FTSE", "SMI20": "^SSMI", "AEX": "^AEX",
    "OMXS30": "^OMX", "BEL20": "^BFX",
    "JP225": "^N225", "CN50": "^FXI", "HK50": "^HSI",
    "ASX200": "^AXJO", "KS11": "^KS11", "TW50": "^TWII",

    # ── Materias primas ──
    "XAUUSD": "GC=F", "XAGUSD": "SI=F", "XPTUSD": "PL=F", "XPDUSD": "PA=F",
    "USOIL": "CL=F", "UKOIL": "BZ=F", "NGAS": "NG=F",
    "CORN": "ZC=F", "WHEAT": "ZW=F", "COPPER": "HG=F",

    # ── Bonos y divisas ──
    "USDX": "DX-Y.NYB", "US10Y": "^TNX", "US30Y": "^TYX", "US02Y": "^2YY",
    "EURUSD": "EURUSD=X", "USDJPY": "USDJPY=X", "GBPUSD": "GBPUSD=X",
    "USDCHF": "USDCHF=X", "USDCAD": "USDCAD=X", "AUDUSD": "AUDUSD=X",
    "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X",

    # ── Crypto ──
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD",
    "SOLUSD": "SOL-USD", "DOGEUSD": "DOGE-USD",

    # ── ETFs USA ──
    "SP500": "SPY", "NASDAQ": "QQQ", "SPY": "SPY", "QQQ": "QQQ",
    "VTI": "VTI", "VXUS": "VXUS", "BND": "BND", "VNQ": "VNQ",
    "XLF": "XLF", "XLK": "XLK", "XLV": "XLV", "XLE": "XLE",
    "XLI": "XLI", "XLP": "XLP", "XLY": "XLY", "XLU": "XLU",
    "XLB": "XLB", "XLRE": "XLRE", "XLC": "XLC", "SMH": "SMH",
    "IBB": "IBB", "KRE": "KRE", "EZU": "EZU", "VGK": "VGK",
    "EWG": "EWG", "EWU": "EWU", "EWQ": "EWQ",
    "GLD": "GLD", "IAU": "IAU", "SLV": "SLV", "GDX": "GDX",
    "DBC": "DBC", "GSG": "GSG",
    "TLT": "TLT", "IEI": "IEI", "SHY": "SHY", "IEF": "IEF",

    # ── ETFs inversos ──
    "SH": "SH", "PSQ": "PSQ", "DOG": "DOG",
    "SQQQ": "SQQQ", "SPXS": "SPXS", "TZA": "TZA",
    "UVXY": "UVXY", "SVXY": "SVXY",

    # ── USA Mega-cap ──
    "AAPL": "AAPL", "MSFT": "MSFT", "GOOGL": "GOOGL",
    "AMZN": "AMZN", "NVDA": "NVDA", "META": "META",
    "TSLA": "TSLA", "AVGO": "AVGO", "TSM": "TSM",
    "BRKB": "BRK-B",

    # ── USA Financieras ──
    "JPM": "JPM", "BAC": "BAC", "WFC": "WFC", "C": "C",
    "GS": "GS", "MS": "MS", "BLK": "BLK", "SCHW": "SCHW",
    "AXP": "AXP", "V": "V", "MA": "MA",

    # ── USA Salud ──
    "UNH": "UNH", "JNJ": "JNJ", "PFE": "PFE", "MRK": "MRK",
    "ABBV": "ABBV", "LLY": "LLY", "TMO": "TMO", "DHR": "DHR",
    "ISRG": "ISRG", "SYK": "SYK",

    # ── USA Consumo ──
    "HD": "HD", "LOW": "LOW", "COST": "COST", "WMT": "WMT",
    "PG": "PG", "KO": "KO", "PEP": "PEP", "MCD": "MCD",
    "SBUX": "SBUX", "NKE": "NKE",

    # ── USA Tecnología ──
    "NFLX": "NFLX", "ADBE": "ADBE", "CRM": "CRM",
    "AMD": "AMD", "INTC": "INTC", "QCOM": "QCOM", "TXN": "TXN",
    "MU": "MU", "ORCL": "ORCL", "IBM": "IBM", "CSCO": "CSCO",
    "AMAT": "AMAT", "LRCX": "LRCX", "NOW": "NOW",
    "UBER": "UBER", "ABNB": "ABNB", "SQ": "SQ", "PYPL": "PYPL",
    "SNAP": "SNAP",

    # ── USA Volátiles / Small caps ──
    "GME": "GME", "AMC": "AMC", "PLTR": "PLTR",
    "MARA": "MARA", "COIN": "COIN", "RIOT": "RIOT",
    "HOOD": "HOOD", "SOFI": "SOFI", "RIVN": "RIVN", "LCID": "LCID",

    # ── Europa Acciones (sufijo .DE Xetra) ──
    "SAP": "SAP.DE", "SIE": "SIE.DE", "ALV": "ALV.DE",
    "MUV2": "MUV2.DE", "BAYN": "BAYN.DE", "BMW": "BMW.DE",
    "VOW3": "VOW3.DE", "DTE": "DTE.DE", "DPW": "DPW.DE",
    "HEI": "HEI.DE", "LIN": "LIN.DE",

    # ── Europa Acciones (sufijo .PA Euronext París) ──
    "AIR": "AIR.PA", "OR": "OR.PA", "MC": "MC.PA",
    "BNP": "BNP.PA", "ACA": "ACA.PA", "SU": "SU.PA",
    "EL": "EL.PA", "TTE": "TTE.PA", "SAN": "SAN.PA",

    # ── España Acciones (sufijo .MC BME) ──
    "IBE": "IBE.MC", "TEF": "TEF.MC", "BBVA": "BBVA.MC",
    "ITX": "ITX.MC", "FER": "FER.MC", "ENG": "ENG.MC",
    "REP": "REP.MC",
}

# Por defecto: si no está en el mapa, pasar el símbolo tal cual
def resolve_symbol(symbol: str) -> str:
    """Resuelve un símbolo interno a ticker de Yahoo Finance"""
    return SYMBOL_MAP.get(symbol, symbol)

# Timeframes: nuestro formato → pandas
TF_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "4h": "4h",
    "1d": "1d", "1w": "1wk",
}


class SandboxPosition:
    """Posición simulada dentro del sandbox"""
    def __init__(self, symbol: str, action: str, volume: float,
                 entry_price: float, sl: float, tp: float, comment: str = ""):
        self.ticket = abs(hash(f"{symbol}{action}{entry_price}{datetime.now()}")) % 100000
        self.symbol = symbol
        self.type = 0 if action == "buy" else 1
        self.type_str = action
        self.volume = volume
        self.price_open = entry_price
        self.price_current = entry_price
        self.sl = sl
        self.tp = tp
        self.profit = 0.0
        self.swap = 0.0
        self.comment = comment
        self.time = datetime.now()


class SandboxBroker:
    """
    Broker sandbox que obtiene datos REALES de Yahoo Finance
    y simula trades sin ejecutarlos realmente.

    Sustituye a MT5. No necesita instalación.
    """

    def __init__(self, config: dict):
        self.cfg = config["broker"]
        self._connected = False
        self._positions: List[SandboxPosition] = []
        self._balance = config["broker"]["account"].get("initial_balance", 50)
        self._equity = self._balance
        self._ticket_counter = 0

    # ── Conexión (simulada) ──

    def connect(self) -> bool:
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance required: pip install yfinance")
        self._connected = True
        print(f"✅ Sandbox broker conectado — Yahoo Finance (GRATIS, datos reales)")
        print(f"   Balance simulado: ${self._balance:.2f}")
        return True

    def disconnect(self):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def check_connection(self):
        if not self._connected:
            raise ConnectionError("Sandbox not connected")

    # ── Datos reales del mercado ──

    def get_rates(self, symbol: str, timeframe: str = "1h",
                  bars: int = 200, from_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Obtiene velas REALES de Yahoo Finance para el símbolo indicado.
        Sin MT5, sin broker, sin coste.
        """
        self.check_connection()

        yahoo_symbol = resolve_symbol(symbol)
        yahoo_tf = TF_MAP.get(timeframe, "1h")

        # Calcular período
        if from_date:
            period = None
        else:
            # Estimar período según timeframe y barras
            period_map = {
                "1m": "7d", "5m": "5d", "15m": "5d", "30m": "1mo",
                "1h": "1mo", "4h": "3mo",
                "1d": "1y", "1wk": "5y",
            }
            period = period_map.get(yahoo_tf, "1mo")

        try:
            _time.sleep(0.35)  # Rate limiting: ~3 calls/sec máx para Yahoo Finance
            if period:
                ticker = yf.Ticker(yahoo_symbol)
                df = ticker.history(period=period, interval=yahoo_tf)
            elif from_date:
                end = datetime.now()
                ticker = yf.Ticker(yahoo_symbol)
                df = ticker.history(start=from_date, end=end, interval=yahoo_tf)
            else:
                return pd.DataFrame()

            if df.empty:
                # Fallback: probar períodos más cortos (futuros/commodities)
                saved = False
                for fb in ["5d", "1mo", "3mo"]:
                    if fb != period:
                        _time.sleep(0.2)
                        fb_df = ticker.history(period=fb, interval=yahoo_tf)
                        if not fb_df.empty:
                            df = fb_df
                            print(f"   ✓ fallback {yahoo_symbol} con período {fb} → {len(df)} velas")
                            saved = True
                            break
                if not saved:
                    print(f"⚠️  Yahoo Finance: sin datos para {symbol} ({yahoo_symbol})")
                    return pd.DataFrame()

            # Renombrar columnas al formato que espera el bot
            df = df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume",
            })

            # Quitar columnas extra
            for c in ["Dividends", "Stock Splits"]:
                if c in df.columns:
                    df.drop(columns=[c], inplace=True)

            # Limitar número de barras
            if len(df) > bars:
                df = df.tail(bars)

            df.index.name = "time"

            print(f"📡 Yahoo Finance: {symbol} ({yahoo_symbol}) → {len(df)} velas {timeframe}")
            return df

        except Exception as e:
            print(f"⚠️  Yahoo Finance error ({symbol}): {e}")
            return pd.DataFrame()

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Información del símbolo (precio actual, spread estimado)"""
        df = self.get_rates(symbol, "1h", 2)
        if df.empty:
            return None
        last = df.iloc[-1]
        return {
            "name": symbol,
            "spread": 1,
            "digits": 2,
            "point": 0.01,
            "bid": last["close"],
            "ask": last["close"] * 1.0001,
            "volume_min": 0.01,
            "volume_max": 10.0,
            "volume_step": 0.01,
        }

    # ── Validación de símbolos al arranque ──

    def validate_symbols(self, symbols: list) -> dict:
        """Comprueba qué símbolos de Yahoo Finance responden correctamente"""
        results = {"ok": [], "fail": []}
        for s in symbols:
            y = resolve_symbol(s)
            try:
                _time.sleep(0.35)
                ticker = yf.Ticker(y)
                info = ticker.history(period="5d", interval="1d")
                if not info.empty:
                    results["ok"].append(s)
                else:
                    results["fail"].append((s, "sin datos"))
            except Exception as e:
                results["fail"].append((s, str(e)[:60]))
        return results

    # ── Trading simulado ──

    def get_positions(self) -> List[Dict[str, Any]]:
        """Lista de posiciones abiertas simuladas"""
        # Actualizar profit con precios actuales
        updated = []
        for pos in self._positions:
            df = self.get_rates(pos.symbol, "1h", 1)
            if not df.empty:
                current = df.iloc[-1]["close"]
                pos.price_current = current
                if pos.type_str == "buy":
                    pos.profit = (current - pos.price_open) * pos.volume * 100
                else:
                    pos.profit = (pos.price_open - current) * pos.volume * 100
            updated.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "buy" if pos.type == 0 else "sell",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "swap": 0,
                "comment": pos.comment,
                "open_time": pos.time,
            })
        return updated

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        for pos in self._positions:
            if pos.symbol == symbol:
                df = self.get_rates(symbol, "1h", 1)
                if not df.empty:
                    pos.price_current = df.iloc[-1]["close"]
                return {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                }
        return None

    def has_open_position(self, symbol: str) -> bool:
        return any(p.symbol == symbol for p in self._positions)

    def open_trade(self, symbol: str, order_type: str, volume: float,
                   sl: Optional[float] = None, tp: Optional[float] = None,
                   comment: str = "Sandbox", magic: int = 0) -> Optional[int]:
        """
        Simula apertura de un trade (no ejecuta realmente).
        Devuelve ticket si se abre correctamente.
        """
        # Obtener precio actual
        df = self.get_rates(symbol, "1h", 1)
        if df.empty:
            return None

        price = df.iloc[-1]["close"]

        # Crear posición simulada
        position = SandboxPosition(
            symbol=symbol,
            action=order_type,
            volume=volume,
            entry_price=price,
            sl=sl or 0,
            tp=tp or 0,
            comment=comment,
        )

        self._positions.append(position)
        cost = price * volume

        print(f"📋 [SANDBOX] {order_type.upper()} {symbol} vol={volume} @ ${price:.2f} "
              f"→ ticket #{position.ticket}")

        return position.ticket

    def close_trade(self, ticket: int, comment: str = "") -> bool:
        """Cierra una posición simulada"""
        pos = next((p for p in self._positions if p.ticket == ticket), None)
        if not pos:
            return False

        df = self.get_rates(pos.symbol, "1h", 1)
        close_price = df.iloc[-1]["close"] if not df.empty else pos.price_open

        if pos.type_str == "buy":
            profit = (close_price - pos.price_open) * pos.volume * 100
        else:
            profit = (pos.price_open - close_price) * pos.volume * 100

        self._balance += profit
        self._positions = [p for p in self._positions if p.ticket != ticket]

        print(f"📋 [SANDBOX] Close #{ticket} {pos.symbol} → Profit: ${profit:.2f}")

        return True

    def close_all_positions(self) -> int:
        count = 0
        for pos in list(self._positions):
            if self.close_trade(pos.ticket):
                count += 1
        return count

    # ── Account ──

    def get_balance(self) -> float:
        total_pnl = 0
        for pos in self._positions:
            df = self.get_rates(pos.symbol, "1h", 1)
            if not df.empty:
                current = df.iloc[-1]["close"]
                if pos.type_str == "buy":
                    total_pnl += (current - pos.price_open) * pos.volume * 100
                else:
                    total_pnl += (pos.price_open - current) * pos.volume * 100
        return self._balance + total_pnl

    def get_equity(self) -> float:
        return self.get_balance()

    def get_account_summary(self) -> dict:
        positions = self.get_positions()
        total_pnl = sum(p["profit"] for p in positions)
        return {
            "connected": True,
            "login": "sandbox",
            "server": "Yahoo Finance",
            "balance": self._balance,
            "equity": self._balance + total_pnl,
            "margin": 0,
            "margin_free": self._balance + total_pnl,
            "margin_level": 0,
            "profit": total_pnl,
            "leverage": 1,
            "currency": "USD",
        }


# Factory function — usada desde engine.py en modo sandbox
def create_sandbox_broker(config: dict) -> SandboxBroker:
    return SandboxBroker(config)