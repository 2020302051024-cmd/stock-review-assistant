from __future__ import annotations

import pandas as pd


def calculate_ma(df: pd.DataFrame, windows: list[int] | None = None) -> pd.DataFrame:
    windows = windows or [5, 10, 20, 60]
    result = df.copy()
    for window in windows:
        result[f"ma{window}"] = result["close"].rolling(window=window).mean()
    return result


def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    ema12 = result["close"].ewm(span=12, adjust=False).mean()
    ema26 = result["close"].ewm(span=26, adjust=False).mean()
    result["dif"] = ema12 - ema26
    result["dea"] = result["dif"].ewm(span=9, adjust=False).mean()
    result["macd"] = (result["dif"] - result["dea"]) * 2
    return result


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    result = df.copy()
    delta = result["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.mask(avg_loss == 0)
    result["rsi"] = 100 - (100 / (1 + rs))
    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    result = calculate_ma(df)
    result = calculate_macd(result)
    result = calculate_rsi(result)
    result["volume_ma5"] = result["volume"].rolling(window=5).mean()
    result["volume_change_rate"] = result["volume"].pct_change()
    result["pct_change"] = result["close"].pct_change()
    result["short_term_return_5d"] = result["close"].pct_change(periods=5)
    return result
