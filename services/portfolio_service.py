from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from database.db import db_connection


VALID_MARKETS = ["A股", "港股", "美股"]


def _clean_holding_payload(data: dict[str, Any]) -> dict[str, Any]:
    stock_code = str(data.get("stock_code", "")).strip()
    stock_name = str(data.get("stock_name", "")).strip()
    market = str(data.get("market", "")).strip()
    industry = str(data.get("industry", "")).strip()
    investment_logic = str(data.get("investment_logic", "")).strip()
    note = str(data.get("note", "")).strip()
    is_watchlist = 1 if data.get("is_watchlist") else 0

    if not stock_code:
        raise ValueError("股票代码不能为空")
    if not stock_name:
        raise ValueError("股票名称不能为空")
    if market not in VALID_MARKETS:
        raise ValueError("市场必须是 A股 / 港股 / 美股")

    buy_price = float(data.get("buy_price", 0))
    quantity = int(data.get("quantity", 0))
    if buy_price <= 0:
        raise ValueError("买入价格必须大于 0")
    if quantity <= 0:
        raise ValueError("持仓数量必须大于 0")

    buy_date = data.get("buy_date") or date.today()
    if isinstance(buy_date, date):
        buy_date = buy_date.isoformat()
    else:
        buy_date = str(buy_date)

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "market": market,
        "buy_price": buy_price,
        "quantity": quantity,
        "buy_date": buy_date,
        "industry": industry,
        "investment_logic": investment_logic,
        "is_watchlist": is_watchlist,
        "note": note,
    }


def add_holding(data: dict[str, Any]) -> int:
    payload = _clean_holding_payload(data)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO holdings (
                stock_code, stock_name, market, buy_price, quantity, buy_date,
                industry, investment_logic, is_watchlist, note
            )
            VALUES (
                :stock_code, :stock_name, :market, :buy_price, :quantity, :buy_date,
                :industry, :investment_logic, :is_watchlist, :note
            )
            """,
            payload,
        )
        return int(cursor.lastrowid)


def update_holding(holding_id: int, data: dict[str, Any]) -> None:
    payload = _clean_holding_payload(data)
    payload["id"] = int(holding_id)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE holdings
            SET stock_code = :stock_code,
                stock_name = :stock_name,
                market = :market,
                buy_price = :buy_price,
                quantity = :quantity,
                buy_date = :buy_date,
                industry = :industry,
                investment_logic = :investment_logic,
                is_watchlist = :is_watchlist,
                note = :note,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """,
            payload,
        )
        if cursor.rowcount == 0:
            raise ValueError("未找到要修改的持仓")


def delete_holding(holding_id: int) -> None:
    with db_connection() as conn:
        cursor = conn.execute("DELETE FROM holdings WHERE id = ?", (int(holding_id),))
        if cursor.rowcount == 0:
            raise ValueError("未找到要删除的持仓")


def get_holding(holding_id: int) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM holdings WHERE id = ?", (int(holding_id),)).fetchone()
    return dict(row) if row else None


def list_holdings() -> list[dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM holdings
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def holdings_dataframe() -> pd.DataFrame:
    rows = list_holdings()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "stock_code",
                "stock_name",
                "market",
                "buy_price",
                "quantity",
                "buy_date",
                "industry",
                "investment_logic",
                "is_watchlist",
                "note",
            ]
        )
    return pd.DataFrame(rows)
