from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from database.db import db_connection
from services.user_context import resolve_user_id


VALID_MARKETS = ["A股", "港股", "美股"]

IMPORT_TEMPLATE_COLUMNS = [
    "股票代码",
    "股票名称",
    "买入价格",
    "持仓数量",
    "买入日期",
    "所属市场",
    "所属行业",
    "投资逻辑",
    "重点监控",
    "备注",
]

IMPORT_COLUMN_ALIASES = {
    "股票代码": "stock_code",
    "代码": "stock_code",
    "stock_code": "stock_code",
    "股票名称": "stock_name",
    "名称": "stock_name",
    "stock_name": "stock_name",
    "买入价格": "buy_price",
    "买入价": "buy_price",
    "成本价": "buy_price",
    "buy_price": "buy_price",
    "持仓数量": "quantity",
    "数量": "quantity",
    "quantity": "quantity",
    "买入日期": "buy_date",
    "日期": "buy_date",
    "buy_date": "buy_date",
    "所属市场": "market",
    "市场": "market",
    "market": "market",
    "所属行业": "industry",
    "行业": "industry",
    "industry": "industry",
    "投资逻辑": "investment_logic",
    "逻辑": "investment_logic",
    "investment_logic": "investment_logic",
    "重点监控": "is_watchlist",
    "watchlist": "is_watchlist",
    "is_watchlist": "is_watchlist",
    "备注": "note",
    "note": "note",
}

IMPORT_SAMPLE_ROWS = [
    {
        "股票代码": "600036",
        "股票名称": "招商银行",
        "买入价格": 40.00,
        "持仓数量": 100,
        "买入日期": "2026-07-15",
        "所属市场": "A股",
        "所属行业": "银行 / 金融",
        "投资逻辑": "观察银行龙头的分红、资产质量和估值修复。",
        "重点监控": "是",
        "备注": "示例行，导入前请替换为真实持仓。",
    },
    {
        "股票代码": "300750",
        "股票名称": "宁德时代",
        "买入价格": 250.00,
        "持仓数量": 100,
        "买入日期": "2026-07-15",
        "所属市场": "A股",
        "所属行业": "新能源 / 动力电池",
        "投资逻辑": "观察动力电池龙头的毛利率、海外业务和行业景气度。",
        "重点监控": "否",
        "备注": "示例行，导入前请替换为真实持仓。",
    },
]


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


def add_holding(data: dict[str, Any], user_id: int | None = None) -> int:
    payload = _clean_holding_payload(data)
    payload["user_id"] = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO holdings (
                user_id, stock_code, stock_name, market, buy_price, quantity, buy_date,
                industry, investment_logic, is_watchlist, note
            )
            VALUES (
                :user_id, :stock_code, :stock_name, :market, :buy_price, :quantity, :buy_date,
                :industry, :investment_logic, :is_watchlist, :note
            )
            """,
            payload,
        )
        return int(cursor.lastrowid)


def build_import_template_dataframe() -> pd.DataFrame:
    return pd.DataFrame(IMPORT_SAMPLE_ROWS, columns=IMPORT_TEMPLATE_COLUMNS)


def normalize_import_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a user-uploaded holding table into internal field names."""
    if df.empty:
        raise ValueError("导入表格为空")

    renamed = {}
    for column in df.columns:
        key = str(column).strip()
        if key in IMPORT_COLUMN_ALIASES:
            renamed[column] = IMPORT_COLUMN_ALIASES[key]

    normalized = df.rename(columns=renamed)
    required = ["stock_code", "stock_name", "buy_price", "quantity", "buy_date"]
    missing = [field for field in required if field not in normalized.columns]
    if missing:
        labels = {
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "buy_price": "买入价格",
            "quantity": "持仓数量",
            "buy_date": "买入日期",
        }
        raise ValueError("缺少必填列：" + "、".join(labels[item] for item in missing))

    for optional, default in {
        "market": "A股",
        "industry": "",
        "investment_logic": "",
        "is_watchlist": False,
        "note": "",
    }.items():
        if optional not in normalized.columns:
            normalized[optional] = default

    columns = [
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
    normalized = normalized[columns].copy()
    normalized = normalized.dropna(how="all")
    normalized["stock_code"] = normalized["stock_code"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    normalized["stock_name"] = normalized["stock_name"].astype(str).str.strip()
    normalized["market"] = normalized["market"].fillna("A股").astype(str).str.strip()
    normalized["industry"] = normalized["industry"].fillna("").astype(str).str.strip()
    normalized["investment_logic"] = normalized["investment_logic"].fillna("").astype(str).str.strip()
    normalized["note"] = normalized["note"].fillna("").astype(str).str.strip()
    normalized["buy_price"] = pd.to_numeric(normalized["buy_price"], errors="coerce")
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce").fillna(0).astype(int)
    normalized["buy_date"] = pd.to_datetime(normalized["buy_date"], errors="coerce").dt.date
    normalized["is_watchlist"] = normalized["is_watchlist"].map(_parse_watchlist_value)
    return normalized


def batch_add_holdings(df: pd.DataFrame, user_id: int | None = None) -> dict[str, Any]:
    """Import holdings row by row and return successes plus row-level errors."""
    normalized = normalize_import_dataframe(df)
    successes = []
    errors = []
    for index, row in normalized.iterrows():
        row_number = int(index) + 2
        payload = row.to_dict()
        try:
            if pd.isna(payload.get("buy_date")):
                raise ValueError("买入日期格式不正确")
            holding_id = add_holding(payload, user_id=user_id)
            successes.append(
                {
                    "row": row_number,
                    "id": holding_id,
                    "stock_code": payload["stock_code"],
                    "stock_name": payload["stock_name"],
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "row": row_number,
                    "stock_code": payload.get("stock_code", ""),
                    "stock_name": payload.get("stock_name", ""),
                    "error": str(exc),
                }
            )
    return {"successes": successes, "errors": errors, "preview": normalized}


def _parse_watchlist_value(value: Any) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "是", "重点", "重点监控"}


def update_holding(holding_id: int, data: dict[str, Any], user_id: int | None = None) -> None:
    payload = _clean_holding_payload(data)
    payload["id"] = int(holding_id)
    payload["user_id"] = resolve_user_id(user_id)
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
            WHERE id = :id AND user_id = :user_id
            """,
            payload,
        )
        if cursor.rowcount == 0:
            raise ValueError("未找到要修改的持仓")


def delete_holding(holding_id: int, user_id: int | None = None) -> None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM holdings WHERE id = ? AND user_id = ?",
            (int(holding_id), owner_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("未找到要删除的持仓")


def get_holding(holding_id: int, user_id: int | None = None) -> dict[str, Any] | None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM holdings WHERE id = ? AND user_id = ?",
            (int(holding_id), owner_id),
        ).fetchone()
    return dict(row) if row else None


def list_holdings(user_id: int | None = None) -> list[dict[str, Any]]:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM holdings
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (owner_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def holdings_dataframe(user_id: int | None = None) -> pd.DataFrame:
    rows = list_holdings(user_id=user_id)
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
