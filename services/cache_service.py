from __future__ import annotations

import json
from typing import Any

from database.db import db_connection


def get_json_cache(key: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute("SELECT value, updated_at FROM app_cache WHERE key = ?", (key,)).fetchone()
    if not row:
        return None
    try:
        return {"value": json.loads(row["value"]), "updated_at": row["updated_at"]}
    except json.JSONDecodeError:
        return None


def set_json_cache(key: str, value: dict[str, Any]) -> None:
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_cache (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, json.dumps(value, ensure_ascii=False, default=str)),
        )

