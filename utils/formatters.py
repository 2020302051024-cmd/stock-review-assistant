from __future__ import annotations

def format_money(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}"


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.2f}%"


def pnl_label(value: float | int | None) -> str:
    if value is None:
        return "未获取"
    if value > 0:
        return "盈利"
    if value < 0:
        return "亏损"
    return "持平"
