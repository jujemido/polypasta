"""
Indicators Module — Technical indicators.

Cada indicador es una función pura: recibe DataFrame, devuelve Series/DataFrame.
Fácil de añadir: solo escribe una función aquí y úsala en cualquier estrategia.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple


def SMA(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """Simple Moving Average"""
    return df[column].rolling(window=period).mean()


def EMA(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """Exponential Moving Average"""
    return df[column].ewm(span=period, adjust=False).mean()


def RSI(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """Relative Strength Index"""
    delta = df[column].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def BollingerBands(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    column: str = "close",
) -> pd.DataFrame:
    """Bollinger Bands: middle, upper, lower, bandwidth"""
    sma = SMA(df, period, column)
    std = df[column].rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    bandwidth = (upper - lower) / sma
    return pd.DataFrame({
        "bb_middle": sma,
        "bb_upper": upper,
        "bb_lower": lower,
        "bb_bandwidth": bandwidth,
        "bb_percent_b": (df[column] - lower) / (upper - lower),
    })


def MACD(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close",
) -> pd.DataFrame:
    """MACD: line, signal, histogram"""
    ema_fast = EMA(df, fast, column)
    ema_slow = EMA(df, slow, column)
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return pd.DataFrame({
        "macd": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
    })


def ATR(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.Series:
    """Average True Range"""
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def VolumeSMA(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volume Simple Moving Average"""
    return df["volume"].rolling(window=period).mean()


def OBV(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume"""
    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    return obv


def Stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """Stochastic Oscillator %K and %D"""
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    k = 100 * ((df["close"] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def apply_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todos los indicadores disponibles al DataFrame"""
    df = df.copy()

    # Fallback para columnas faltantes
    if "high" not in df.columns:
        df["high"] = df["close"] * 1.002
    if "low" not in df.columns:
        df["low"] = df["close"] * 0.998
    if "volume" not in df.columns:
        df["volume"] = 1

    # SMA
    for p in [10, 20, 50, 200]:
        df[f"sma_{p}"] = SMA(df, p)

    # EMA
    for p in [12, 26]:
        df[f"ema_{p}"] = EMA(df, p)

    # RSI
    for p in [7, 14, 21]:
        df[f"rsi_{p}"] = RSI(df, p)

    # Bollinger
    bb = BollingerBands(df)
    df = pd.concat([df, bb], axis=1)

    # MACD
    macd = MACD(df)
    df = pd.concat([df, macd], axis=1)

    # ATR
    df["atr_14"] = ATR(df, 14)

    # Volume
    df["volume_sma_20"] = VolumeSMA(df)
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

    return df