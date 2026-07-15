from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from database.db import db_connection
from services.user_context import resolve_user_id


TRADE_ACTIONS = ["买入", "卖出", "加仓", "减仓", "观察", "取消计划"]
EMOTION_OPTIONS = ["平静", "犹豫", "担心", "冲动", "贪心", "后悔", "其他"]


def add_trade_log(data: dict[str, Any], user_id: int | None = None) -> int:
    payload = _clean_payload(data)
    payload["user_id"] = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trade_logs (
                user_id, holding_id, stock_code, stock_name, action, trade_date,
                price, quantity, reason, emotion, discipline_note
            ) VALUES (
                :user_id, :holding_id, :stock_code, :stock_name, :action, :trade_date,
                :price, :quantity, :reason, :emotion, :discipline_note
            )
            """,
            payload,
        )
        return int(cursor.lastrowid)


def update_trade_log(
    log_id: int,
    data: dict[str, Any],
    user_id: int | None = None,
) -> None:
    payload = _clean_payload(data)
    payload["id"] = int(log_id)
    payload["user_id"] = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE trade_logs SET
                holding_id = :holding_id,
                stock_code = :stock_code,
                stock_name = :stock_name,
                action = :action,
                trade_date = :trade_date,
                price = :price,
                quantity = :quantity,
                reason = :reason,
                emotion = :emotion,
                discipline_note = :discipline_note,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND user_id = :user_id
            """,
            payload,
        )
        if cursor.rowcount == 0:
            raise ValueError("未找到要修改的交易日志")


def delete_trade_log(log_id: int, user_id: int | None = None) -> None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM trade_logs WHERE id = ? AND user_id = ?",
            (int(log_id), owner_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("未找到要删除的交易日志")


def get_trade_log(log_id: int, user_id: int | None = None) -> dict[str, Any] | None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trade_logs WHERE id = ? AND user_id = ?",
            (int(log_id), owner_id),
        ).fetchone()
    return dict(row) if row else None


def list_trade_logs(
    stock_code: str | None = None,
    limit: int = 200,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    owner_id = resolve_user_id(user_id)
    params: list[Any] = [owner_id]
    where = "WHERE user_id = ?"
    if stock_code:
        where += " AND stock_code = ?"
        params.append(stock_code.strip())
    params.append(int(limit))
    with db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT *, price * quantity AS amount
            FROM trade_logs
            {where}
            ORDER BY trade_date DESC, created_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def trade_log_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "trade_count": 0, "total_amount": 0.0, "impulsive_count": 0}
    frame = pd.DataFrame(rows)
    trade_actions = {"买入", "卖出", "加仓", "减仓"}
    traded = frame[frame["action"].isin(trade_actions)]
    amount = pd.to_numeric(traded.get("amount"), errors="coerce").fillna(0).sum()
    return {
        "count": len(frame),
        "trade_count": len(traded),
        "total_amount": float(amount),
        "impulsive_count": int(frame["emotion"].isin(["冲动", "贪心"]).sum()),
    }


def trade_logs_to_context(rows: list[dict[str, Any]], limit: int = 12) -> str:
    if not rows:
        return "近期交易日志：无。"
    lines = ["近期交易日志（仅用于纪律复盘，不代表系统建议）："]
    for item in rows[:limit]:
        lines.append(
            "- "
            f"{item['trade_date']} {item['stock_name']}({item['stock_code']}) {item['action']}，"
            f"价格 {float(item.get('price') or 0):.2f}，数量 {int(item.get('quantity') or 0)}，"
            f"情绪 {item.get('emotion') or '未记录'}，"
            f"理由 {item.get('reason') or '未记录'}，"
            f"纪律复盘 {item.get('discipline_note') or '未记录'}"
        )
    return "\n".join(lines)


def _clean_payload(data: dict[str, Any]) -> dict[str, Any]:
    stock_code = str(data.get("stock_code", "")).strip()
    stock_name = str(data.get("stock_name", "")).strip()
    action = str(data.get("action", "")).strip()
    if not stock_code or not stock_name:
        raise ValueError("股票代码和名称不能为空")
    if action not in TRADE_ACTIONS:
        raise ValueError("交易动作不在允许范围内")

    raw_date = data.get("trade_date") or date.today()
    trade_date = raw_date.isoformat() if isinstance(raw_date, date) else str(raw_date)
    price = float(data.get("price", 0) or 0)
    quantity = int(data.get("quantity", 0) or 0)
    if action in {"买入", "卖出", "加仓", "减仓"} and (price <= 0 or quantity <= 0):
        raise ValueError("实际交易记录的价格和数量必须大于 0")

    holding_id = data.get("holding_id")
    return {
        "holding_id": int(holding_id) if holding_id else None,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "action": action,
        "trade_date": trade_date,
        "price": max(0.0, price),
        "quantity": max(0, quantity),
        "reason": str(data.get("reason", "")).strip(),
        "emotion": str(data.get("emotion", "")).strip(),
        "discipline_note": str(data.get("discipline_note", "")).strip(),
    }
