from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from database.db import db_connection
from services.market_data import MarketDataResult, get_cached_price, get_current_price_with_kline
from services.market_snapshot_service import save_price_snapshot
from services.user_context import resolve_user_id


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
    market_results: dict[int, MarketDataResult] | None = None,
    market_days: int = 5,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manual_prices = manual_prices or {}
    rows = []
    errors = []
    market_results = market_results if market_results is not None else {}
    fetched_results = _fetch_market_results(holdings, manual_prices, market_days) if fetch_market_price else {}

    for holding in holdings:
        holding_id = int(holding["id"])
        price = manual_prices.get(holding_id)
        price_source = "手动输入" if price is not None else ""

        if price is not None:
            try:
                save_price_snapshot(
                    holding["stock_code"], holding["market"], float(price), "用户手动输入"
                )
            except Exception:
                pass

        if price is None and fetch_market_price:
            result = fetched_results.get(holding_id)
            if result is None:
                result = MarketDataResult(ok=False, error="行情任务未返回结果")
            market_results[holding_id] = result
            if result.ok:
                price = result.price
                price_source = result.source
                if result.error and result.source.startswith("缓存"):
                    errors.append(
                        f"{holding['stock_name']}({holding['stock_code']})：实时行情失败，"
                        f"已使用{result.source}。原始错误：{result.error}"
                    )
            else:
                errors.append(f"{holding['stock_name']}({holding['stock_code']})：{result.error}")
        elif price is None:
            cached = get_cached_price(holding["stock_code"], holding["market"])
            if cached.ok:
                price = cached.price
                price_source = cached.source

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
    df["pnl_contribution"] = pd.to_numeric(df["floating_pnl"], errors="coerce").fillna(0)

    summary = {
        "total_cost": total_cost,
        "total_market_value": total_market_value,
        "total_floating_pnl": total_floating_pnl,
        "total_return_rate": total_return_rate,
        "errors": errors,
    }
    return df.sort_values("pnl_contribution", ascending=False), summary


def _fetch_market_results(
    holdings: list[dict[str, Any]],
    manual_prices: dict[int, float],
    market_days: int,
) -> dict[int, MarketDataResult]:
    targets = [item for item in holdings if int(item["id"]) not in manual_prices]
    if not targets:
        return {}

    results: dict[int, MarketDataResult] = {}
    max_workers = min(4, len(targets))
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="market-data") as executor:
        futures = {
            executor.submit(
                get_current_price_with_kline,
                holding["stock_code"],
                holding["market"],
                market_days,
            ): int(holding["id"])
            for holding in targets
        }
        for future in as_completed(futures):
            holding_id = futures[future]
            try:
                results[holding_id] = future.result()
            except Exception as exc:
                results[holding_id] = MarketDataResult(ok=False, error=f"行情任务异常：{exc}")
    return results


def save_ai_report(
    report_type: str,
    title: str,
    source_text: str,
    ai_result: str,
    user_id: int | None = None,
) -> int:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ai_reports (user_id, report_type, title, source_text, ai_result)
            VALUES (?, ?, ?, ?, ?)
            """,
            (owner_id, report_type, title, source_text, ai_result),
        )
        return int(cursor.lastrowid)


def list_ai_reports(
    report_type: str | None = None,
    limit: int = 20,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        if report_type:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_reports
                WHERE user_id = ? AND report_type = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (owner_id, report_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT *
                FROM ai_reports
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (owner_id, limit),
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
