from __future__ import annotations

from typing import Any

from database.db import db_connection
from services.user_context import resolve_user_id


def get_setting(key: str, default: str = "", user_id: int | None = None) -> str:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM user_settings WHERE user_id = ? AND key = ?",
            (owner_id, key),
        ).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: Any, user_id: int | None = None) -> None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (owner_id, key, str(value)),
        )


def get_bool_setting(key: str, default: bool = False, user_id: int | None = None) -> bool:
    raw = get_setting(key, "true" if default else "false", user_id=user_id).strip().lower()
    return raw in {"1", "true", "yes", "on", "启用"}


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * 8}{value[-visible:]}"
