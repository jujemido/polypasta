"""
Time utils — Utilidades para manejo de tiempos, fechas y timeframes.
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional


def timeframe_to_minutes(timeframe: str) -> int:
    mapping = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240,
        "1d": 1440, "1w": 10080,
    }
    return mapping.get(timeframe, 60)


def minutes_to_timeframe(minutes: int) -> str:
    rev = {1: "1m", 5: "5m", 15: "15m", 30: "30m",
           60: "1h", 240: "4h", 1440: "1d", 10080: "1w"}
    return rev.get(minutes, "1h")


def is_market_open(symbol: str) -> Tuple[bool, str]:
    """
    ¿Está el mercado abierto para este símbolo?
    Devuelve (bool, "razón")
    """
    now = datetime.now()
    wd = now.weekday()
    h = now.hour

    if wd >= 5:
        return (False, "Fin de semana")

    sym_upper = symbol.upper()

    # Crypto: 24/7
    if any(c in sym_upper for c in ["BTC", "ETH", "SOL", "DOGE"]):
        return (True, "24/7")

    # Forex: 24/5 (domingo 22:00 UTC - viernes 22:00 UTC)
    if any(c in sym_upper for c in ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "USDX"]):
        return (True, "Forex 24/5")

    # USA equities & indices: 9:30-16:00 ET = ~14:30-21:00 CET/CEST
    if sym_upper in ("US100", "US500", "US30", "US2000", "VIX", "SPY", "QQQ",
                     "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                     "XLF", "XLK", "XLV", "XLE", "XLI", "XLP", "XLY", "XLU",
                     "XLB", "XLRE", "XLC", "SMH", "IBB", "KRE",
                     "JPM", "V", "MA", "UNH", "HD", "PG", "COST",
                     "BRKB", "NFLX", "ADBE", "CRM", "AMD", "INTC", "QCOM",
                     "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP",
                     "JNJ", "PFE", "MRK", "ABBV", "LLY", "TMO", "DHR", "ISRG", "SYK",
                     "LOW", "WMT", "KO", "PEP", "MCD", "SBUX", "NKE",
                     "ORCL", "IBM", "CSCO", "TXN", "MU",
                     "AVGO", "TSM", "NOW", "UBER", "ABNB", "SQ", "PYPL", "SNAP",
                     "GME", "AMC", "PLTR", "MARA", "COIN", "RIOT", "HOOD", "SOFI",
                     "RIVN", "LCID", "AMAT", "LRCX", "SYK",
                     "UNH", "TMO", "DHR", "ISRG",
                     "TLT", "IEI", "SHY", "IEF",
                     "SH", "PSQ", "DOG", "SQQQ", "SPXS", "TZA", "UVXY", "SVXY",
                     "VTI", "VXUS", "BND", "VNQ",
                     "GLD", "IAU", "SLV", "GDX", "DBC", "GSG", "EZU", "VGK", "EWG", "EWU", "EWQ"):
        if h < 14 or h >= 22:
            return (False, "Mercado USA cerrado (14:30-21:00 CET)")
        return (True, "Mercado USA abierto")

    # Europe equities & indices: 8:00-16:30 CET
    if sym_upper in ("IBEX35", "DAX40", "GER40", "CAC40", "EUROSTOXX50",
                     "UK100", "FTSE100", "SMI20", "AEX", "OMXS30", "BEL20",
                     "SAP", "SIE", "ALV", "MUV2", "BAYN", "BMW", "VOW3",
                     "DTE", "DPW", "HEI", "LIN", "AIR", "OR", "MC",
                     "SAN", "BNP", "ACA", "SU", "EL", "TTE",
                     "IBE", "TEF", "BBVA", "ITX", "FER", "ENG", "REP"):
        if h < 8 or h >= 17:
            return (False, "Mercado europeo cerrado (8:00-16:30 CET)")
        return (True, "Mercado europeo abierto")

    # Asia
    if sym_upper in ("JP225", "NIKKEI", "CN50", "HK50", "ASX200", "KS11", "TW50"):
        if h < 1 or h >= 8:
            return (False, "Mercado asiático cerrado")
        return (True, "Mercado asiático abierto")

    # Commodities: Gold, Oil - follow USA hours approximately
    if sym_upper in ("XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "USOIL", "UKOIL",
                     "NGAS", "CORN", "WHEAT", "COPPER", "GC=F"):
        return (True, "Commodities")

    # Default: assume open
    return (True, "Sin restricción horaria")


def next_candle_time(timeframe: str) -> datetime:
    now = datetime.now()
    minutes = timeframe_to_minutes(timeframe)
    current_minute = now.minute
    next_minute = ((current_minute // minutes) + 1) * minutes
    next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=next_minute)
    if next_time <= now:
        next_time += timedelta(minutes=minutes)
    return next_time


def format_timedelta(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    if seconds > 0 and hours == 0: parts.append(f"{seconds}s")
    return " ".join(parts) if parts else "0s"