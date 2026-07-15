from __future__ import annotations

import json
from typing import Any

import pandas as pd

from database.db import db_connection


def save_price_snapshot(stock_code: str, market: str, price: float, source: str) -> None:
    _upsert_snapshot(stock_code, market, "price", float(price), "", source)


def get_price_snapshot(stock_code: str, market: str) -> dict[str, Any] | None:
    row = _get_snapshot(stock_code, market, "price")
    if not row or row.get("price") is None:
        return None
    return row


def save_kline_snapshot(stock_code: str, market: str, data: pd.DataFrame, source: str) -> None:
    if data is None or data.empty:
        return
    payload = data.copy()
    if "date" in payload.columns:
        payload["date"] = pd.to_datetime(payload["date"]).dt.strftime("%Y-%m-%d")
    data_json = payload.to_json(orient="records", force_ascii=False)
    price = float(pd.to_numeric(payload["close"], errors="coerce").dropna().iloc[-1])
    _upsert_snapshot(stock_code, market, "daily_kline", price, data_json, source)


def get_kline_snapshot(stock_code: str, market: str, days: int = 180) -> dict[str, Any] | None:
    row = _get_snapshot(stock_code, market, "daily_kline")
    if not row or not row.get("data_json"):
        return None
    try:
        records = json.loads(row["data_json"])
        frame = pd.DataFrame(records)
        if frame.empty:
            return None
        frame["date"] = pd.to_datetime(frame["date"])
        for column in ["open", "high", "low", "close", "volume", "amount"]:
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")
        row["data"] = frame.tail(days).reset_index(drop=True)
        return row
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def list_market_snapshots(limit: int = 50) -> list[dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT stock_code, market, snapshot_type, price, source, captured_at
            FROM market_snapshots
            ORDER BY captured_at DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def _upsert_snapshot(
    stock_code: str,
    market: str,
    snapshot_type: str,
    price: float | None,
    data_json: str,
    source: str,
) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO market_snapshots (
                stock_code, market, snapshot_type, price, data_json, source, captured_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(stock_code, market, snapshot_type) DO UPDATE SET
                price = excluded.price,
                data_json = excluded.data_json,
                source = excluded.source,
                captured_at = CURRENT_TIMESTAMP
            """,
            (stock_code.strip(), market.strip(), snapshot_type, price, data_json, source),
        )


def _get_snapshot(stock_code: str, market: str, snapshot_type: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT stock_code, market, snapshot_type, price, data_json, source, captured_at
            FROM market_snapshots
            WHERE stock_code = ? AND market = ? AND snapshot_type = ?
            """,
            (stock_code.strip(), market.strip(), snapshot_type),
        ).fetchone()
    return dict(row) if row else None
