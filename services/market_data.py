from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests

from config import settings


@dataclass
class MarketDataResult:
    ok: bool
    data: pd.DataFrame | None = None
    price: float | None = None
    source: str = ""
    error: str = ""


def _strip_code(stock_code: str) -> str:
    return (
        stock_code.strip()
        .lower()
        .replace("sh", "")
        .replace("sz", "")
        .replace(".sh", "")
        .replace(".sz", "")
    )


def _to_yfinance_symbol(stock_code: str, market: str) -> str:
    code = stock_code.strip().upper()
    if market == "港股" and not code.endswith(".HK"):
        return f"{code.zfill(4)}.HK"
    return code


def _to_a_share_symbol_with_market(stock_code: str) -> str:
    clean_code = _strip_code(stock_code).zfill(6)
    prefix = "sh" if clean_code.startswith(("5", "6", "9")) else "sz"
    return f"{prefix}{clean_code}"


def get_a_share_daily(stock_code: str, days: int = 180) -> MarketDataResult:
    primary_error = ""
    try:
        import akshare as ak

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        clean_code = _strip_code(stock_code)
        errors = []
        df = pd.DataFrame()

        for adjust in ["qfq", ""]:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=clean_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )
                if not df.empty:
                    break
            except Exception as exc:
                errors.append(f"adjust={adjust or '不复权'}: {exc}")

        if df.empty:
            detail = "；".join(errors) if errors else "接口返回空数据"
            primary_error = f"未获取到 A股日K数据：{detail}"
        else:
            df = df.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            df["date"] = pd.to_datetime(df["date"])
            for column in ["open", "high", "low", "close", "volume", "amount"]:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            result = df[["date", "open", "high", "low", "close", "volume", "amount"]].tail(days)
            return MarketDataResult(ok=True, data=result.reset_index(drop=True), source="akshare")
    except Exception as exc:
        primary_error = f"A股行情获取失败：{exc}"

    fallback = get_a_share_daily_tx(stock_code, days)
    if fallback.ok:
        return fallback
    return MarketDataResult(ok=False, error=f"{primary_error or 'A股主行情源失败'}；腾讯历史日K兜底也失败：{fallback.error}")


def get_a_share_daily_tx(stock_code: str, days: int = 180) -> MarketDataResult:
    try:
        import akshare as ak

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
        symbol = _to_a_share_symbol_with_market(stock_code)
        errors = []
        df = pd.DataFrame()
        for adjust in ["qfq", ""]:
            try:
                df = ak.stock_zh_a_hist_tx(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    timeout=settings.REQUEST_TIMEOUT_SECONDS,
                )
                if not df.empty:
                    break
            except Exception as exc:
                errors.append(f"adjust={adjust or '不复权'}: {exc}")

        if df.empty:
            detail = "；".join(errors) if errors else "接口返回空数据"
            return MarketDataResult(ok=False, error=f"腾讯历史日K未获取到数据：{detail}")

        df = df.rename(columns={"amount": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["amount"] = pd.NA
        result = df[["date", "open", "high", "low", "close", "volume", "amount"]].tail(days)
        return MarketDataResult(ok=True, data=result.reset_index(drop=True), source="腾讯历史日K")
    except Exception as exc:
        return MarketDataResult(ok=False, error=f"腾讯历史日K获取失败：{exc}")


def get_a_share_spot_price(stock_code: str) -> MarketDataResult:
    try:
        import akshare as ak

        clean_code = _strip_code(stock_code)
        df = ak.stock_zh_a_spot_em()
        if df.empty:
            return MarketDataResult(ok=False, error="A股实时行情接口返回空数据")

        code_col = "代码"
        price_col = "最新价"
        matched = df[df[code_col].astype(str).str.zfill(6) == clean_code.zfill(6)]
        if matched.empty:
            return MarketDataResult(ok=False, error=f"A股实时行情未找到代码 {clean_code}")
        price = pd.to_numeric(matched.iloc[0][price_col], errors="coerce")
        if pd.isna(price):
            return MarketDataResult(ok=False, error=f"A股实时行情价格为空：{clean_code}")
        return MarketDataResult(ok=True, price=float(price), source="akshare实时行情")
    except Exception as exc:
        return MarketDataResult(ok=False, error=f"A股实时行情获取失败：{exc}")


def get_a_share_tencent_price(stock_code: str) -> MarketDataResult:
    try:
        clean_code = _strip_code(stock_code).zfill(6)
        symbol = _to_a_share_symbol_with_market(stock_code)
        response = requests.get(
            f"https://qt.gtimg.cn/q={symbol}",
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = response.text
        if '="' not in text:
            return MarketDataResult(ok=False, error=f"腾讯行情返回格式异常：{text[:120]}")
        payload = text.split('="', 1)[1].rstrip('";\n')
        parts = payload.split("~")
        if len(parts) < 4:
            return MarketDataResult(ok=False, error=f"腾讯行情字段不足：{text[:120]}")
        price = pd.to_numeric(parts[3], errors="coerce")
        if pd.isna(price) or float(price) <= 0:
            return MarketDataResult(ok=False, error=f"腾讯行情价格为空：{clean_code}")
        return MarketDataResult(ok=True, price=float(price), source="腾讯实时行情")
    except Exception as exc:
        return MarketDataResult(ok=False, error=f"腾讯实时行情获取失败：{exc}")


def get_yfinance_daily(stock_code: str, market: str, days: int = 180) -> MarketDataResult:
    try:
        import yfinance as yf

        symbol = _to_yfinance_symbol(stock_code, market)
        df = yf.Ticker(symbol).history(period=f"{max(days, 30)}d", interval="1d")
        if df.empty:
            return MarketDataResult(ok=False, error="未获取到 yfinance 日K数据")

        df = df.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        df["amount"] = pd.NA
        result = df[["date", "open", "high", "low", "close", "volume", "amount"]].tail(days)
        return MarketDataResult(ok=True, data=result.reset_index(drop=True), source="yfinance")
    except Exception as exc:
        return MarketDataResult(ok=False, error=f"{market} 行情获取失败：{exc}")


def get_daily_kline(stock_code: str, market: str, days: int = 180) -> MarketDataResult:
    if market == "A股":
        return get_a_share_daily(stock_code, days)
    if market in {"港股", "美股"}:
        return get_yfinance_daily(stock_code, market, days)
    return MarketDataResult(ok=False, error="暂不支持该市场")


def get_current_price(stock_code: str, market: str) -> MarketDataResult:
    daily = get_daily_kline(stock_code, market, days=5)
    if not daily.ok or daily.data is None or daily.data.empty:
        if market == "A股":
            spot = get_a_share_spot_price(stock_code)
            if spot.ok:
                return spot
            tencent = get_a_share_tencent_price(stock_code)
            if tencent.ok:
                return tencent
            return MarketDataResult(
                ok=False,
                error=f"{daily.error}；akshare实时行情也失败：{spot.error}；腾讯实时行情也失败：{tencent.error}",
            )
        return MarketDataResult(ok=False, error=daily.error)
    price = float(daily.data.iloc[-1]["close"])
    return MarketDataResult(ok=True, price=price, data=daily.data, source=daily.source)


def get_manual_price_map(rows: list[dict[str, Any]], inputs: dict[int, float | None]) -> dict[int, float]:
    prices: dict[int, float] = {}
    for row in rows:
        value = inputs.get(int(row["id"]))
        if value is not None and float(value) > 0:
            prices[int(row["id"])] = float(value)
    return prices
