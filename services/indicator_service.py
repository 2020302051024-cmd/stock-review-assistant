from __future__ import annotations

from typing import Any

import pandas as pd

from utils.indicators import add_all_indicators


def analyze_kline(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df.empty or len(df) < 20:
        raise ValueError("K线数据不足，至少需要 20 个交易日")

    analyzed = add_all_indicators(df).copy()
    latest = analyzed.iloc[-1]
    previous = analyzed.iloc[-2]

    current_price = float(latest["close"])
    volume_ma5 = latest.get("volume_ma5")
    volume_ratio = None
    if pd.notna(volume_ma5) and float(volume_ma5) > 0:
        volume_ratio = float(latest["volume"]) / float(volume_ma5)

    above_ma = {}
    below_key_ma = []
    for window in [5, 10, 20, 60]:
        ma_value = latest.get(f"ma{window}")
        is_above = bool(pd.notna(ma_value) and current_price >= float(ma_value))
        above_ma[f"MA{window}"] = is_above
        if not is_above and pd.notna(ma_value):
            below_key_ma.append(f"MA{window}")

    pct_change = float(latest.get("pct_change") or 0)
    five_day_return = latest.get("short_term_return_5d")
    five_day_return_value = float(five_day_return) if pd.notna(five_day_return) else None
    is_volume_surge = bool(volume_ratio is not None and volume_ratio >= 1.5)

    signals = {
        "current_price": current_price,
        "ma5": _safe_float(latest.get("ma5")),
        "ma10": _safe_float(latest.get("ma10")),
        "ma20": _safe_float(latest.get("ma20")),
        "ma60": _safe_float(latest.get("ma60")),
        "macd": _safe_float(latest.get("macd")),
        "dif": _safe_float(latest.get("dif")),
        "dea": _safe_float(latest.get("dea")),
        "rsi": _safe_float(latest.get("rsi")),
        "volume": _safe_float(latest.get("volume")),
        "volume_ratio_vs_ma5": volume_ratio,
        "above_ma": above_ma,
        "is_volume_up": bool(is_volume_surge and pct_change > 0),
        "is_volume_down": bool(is_volume_surge and pct_change < 0),
        "below_key_ma": below_key_ma,
        "breaks_below_ma20": _crossed_below(previous, latest, "ma20"),
        "breaks_below_ma60": _crossed_below(previous, latest, "ma60"),
        "short_term_gain_too_high": bool(five_day_return_value is not None and five_day_return_value >= 0.12),
        "five_day_return": five_day_return_value,
        "pct_change": pct_change,
        "trend_summary": _trend_summary(above_ma, latest),
        "risk_notes": _risk_notes(pct_change, volume_ratio, below_key_ma, five_day_return_value, latest),
    }
    return analyzed, signals


def _safe_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _crossed_below(previous: pd.Series, latest: pd.Series, ma_col: str) -> bool:
    prev_ma = previous.get(ma_col)
    latest_ma = latest.get(ma_col)
    if pd.isna(prev_ma) or pd.isna(latest_ma):
        return False
    return bool(previous["close"] >= prev_ma and latest["close"] < latest_ma)


def _trend_summary(above_ma: dict[str, bool], latest: pd.Series) -> str:
    if above_ma.get("MA5") and above_ma.get("MA10") and above_ma.get("MA20"):
        return "短期价格位于多条均线上方，趋势偏强，但仍需结合成交量和消息面确认。"
    if not above_ma.get("MA20") and not above_ma.get("MA60"):
        return "价格低于中长期均线，趋势偏弱，新手应优先关注风险控制。"
    if latest.get("macd", 0) > 0:
        return "走势处于震荡偏积极状态，但还不是单独决策依据。"
    return "走势偏震荡，建议等待更清晰的趋势确认。"


def _risk_notes(
    pct_change: float,
    volume_ratio: float | None,
    below_key_ma: list[str],
    five_day_return: float | None,
    latest: pd.Series,
) -> list[str]:
    notes = []
    if below_key_ma:
        notes.append(f"当前价格低于 {'、'.join(below_key_ma)}，说明对应周期的趋势压力仍在。")
    if volume_ratio is not None and volume_ratio >= 1.5 and pct_change < 0:
        notes.append("出现放量下跌，可能代表分歧或抛压增加，需要谨慎观察。")
    if five_day_return is not None and five_day_return >= 0.12:
        notes.append("近 5 个交易日涨幅较大，新手要警惕追高风险。")
    rsi = latest.get("rsi")
    if pd.notna(rsi) and float(rsi) >= 70:
        notes.append("RSI 高于 70，短线可能偏热，不宜只因上涨而冲动加仓。")
    if pd.notna(rsi) and float(rsi) <= 30:
        notes.append("RSI 低于 30，短线可能超跌，但超跌不等于马上反转。")
    if not notes:
        notes.append("暂无明显单一技术风险，但技术指标只能作为辅助观察。")
    return notes
