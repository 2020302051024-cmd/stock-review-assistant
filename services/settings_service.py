from __future__ import annotations

from typing import Any

from database.db import db_connection


def get_setting(key: str, default: str = "") -> str:
    with db_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: Any) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, str(value)),
        )


def get_bool_setting(key: str, default: bool = False) -> bool:
    raw = get_setting(key, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on", "启用"}


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * 8}{value[-visible:]}"

