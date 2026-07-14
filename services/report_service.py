from __future__ import annotations

from typing import Any

import pandas as pd

from database.db import db_connection
from services.market_data import get_current_price


def calculate_position_pnl(holding: dict[str, Any], current_price: float | None) -> dict[str, Any]:
    buy_price = float(holding["buy_price"])
    quantity = int(holding["quantity"])
    cost = buy_price * quantity

    if current_price is None:
        market_value = None
        pnl = None
        pnl_rate = None
    else:
        market_value = float(current_price) * quantity
        pnl = market_value - cost
        pnl_rate = pnl / cost if cost else 0

    return {
        **holding,
        "cost": cost,
        "current_price": current_price,
        "market_value": market_value,
        "floating_pnl": pnl,
        "return_rate": pnl_rate,
    }


def calculate_portfolio_pnl(
    holdings: list[dict[str, Any]],
    manual_prices: dict[int, float] | None = None,
    fetch_market_price: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manual_prices = manual_prices or {}
    rows = []
    errors = []

    for holding in holdings:
        holding_id = int(holding["id"])
        price = manual_prices.get(holding_id)
        price_source = "手动输入" if price is not None else ""

        if price is None and fetch_market_price:
            result = get_current_price(holding["stock_code"], holding["market"])
            if result.ok:
                price = result.price
                price_source = result.source
            else:
                errors.append(f"{holding['stock_name']}({holding['stock_code']})：{result.error}")

        row = calculate_position_pnl(holding, price)
        row["price_source"] = price_source
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df, {
            "total_cost": 0,
            "total_market_value": 0,
            "total_floating_pnl": 0,
            "total_return_rate": 0,
            "errors": errors,
        }

    total_cost = float(df["cost"].sum())
    total_market_value = float(df["market_value"].dropna().sum())
    total_floating_pnl = float(df["floating_pnl"].dropna().sum())
    total_return_rate = total_floating_pnl / total_cost if total_cost else 0
    df["pnl_contribution"] = df["floating_pnl"].fillna(0)

    summary = {
        "total_cost": total_cost,
        "total_market_value": total_market_value,
        "total_floating_pnl": total_floating_pnl,
        "total_return_rate": total_return_rate,
        "errors": errors,
    }
    return df.sort_values("pnl_contribution", ascending=False), summary


def save_ai_report(report_type: str, title: str, source_text: str, ai_result: str) -> int:
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ai_reports (report_type, title, source_text, ai_result)
            VALUES (?, ?, ?, ?)
            """,
            (report_type, title, source_text, ai_result),
        )
        return int(cursor.lastrowid)


def list_ai_reports(report_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with db_connection() as conn:
        if report_type:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_reports
                WHERE report_type = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (report_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_reports
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def portfolio_context_to_text(
    pnl_df: pd.DataFrame,
    summary: dict[str, Any],
    technical_summaries: list[dict[str, Any]] | None = None,
) -> str:
    technical_summaries = technical_summaries or []
    lines = [
        f"总成本：{summary.get('total_cost', 0):.2f}",
        f"当前市值：{summary.get('total_market_value', 0):.2f}",
        f"总浮动盈亏：{summary.get('total_floating_pnl', 0):.2f}",
        f"总收益率：{summary.get('total_return_rate', 0) * 100:.2f}%",
        "",
        "持仓盈亏明细：",
    ]

    if pnl_df.empty:
        lines.append("暂无持仓。")
    else:
        for _, row in pnl_df.iterrows():
            return_rate = row["return_rate"]
            return_rate_text = "-" if pd.isna(return_rate) else f"{float(return_rate) * 100:.2f}%"
            lines.append(
                "- "
                f"{row['stock_name']}({row['stock_code']}, {row['market']}): "
                f"行业 {row.get('industry', '') or '未填写'}, "
                f"买入价 {row['buy_price']}, 数量 {row['quantity']}, "
                f"当前价 {row['current_price']}, "
                f"浮动盈亏 {row['floating_pnl']}, 收益率 {return_rate_text}, "
                f"投资逻辑 {row.get('investment_logic', '') or '未填写'}, "
                f"重点监控 {'是' if row.get('is_watchlist') else '否'}, "
                f"备注 {row.get('note', '') or '无'}"
            )

    if technical_summaries:
        lines.extend(["", "技术面摘要："])
        for item in technical_summaries:
            lines.append(
                "- "
                f"{item.get('stock_name')}({item.get('stock_code')}): "
                f"当前价 {item.get('current_price')}, "
                f"趋势解释：{item.get('trend_summary')}, "
                f"风险：{'；'.join(item.get('risk_notes', []))}"
            )

    errors = summary.get("errors") or []
    if errors:
        lines.extend(["", "行情获取问题："])
        lines.extend(f"- {error}" for error in errors)

    return "\n".join(lines)
