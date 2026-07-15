from __future__ import annotations

import json
from typing import Any

from database.db import db_connection
from services.user_context import primary_user_id, resolve_user_id


def _scoped_key(key: str, user_id: int) -> str:
    return f"user:{user_id}:{key}"


def get_json_cache(key: str, user_id: int | None = None) -> dict[str, Any] | None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        row = conn.execute(
            "SELECT value, updated_at FROM app_cache WHERE key = ?",
            (_scoped_key(key, owner_id),),
        ).fetchone()
        if not row and owner_id == primary_user_id():
            row = conn.execute(
                "SELECT value, updated_at FROM app_cache WHERE key = ?", (key,)
            ).fetchone()
    if not row:
        return None
    try:
        return {"value": json.loads(row["value"]), "updated_at": row["updated_at"]}
    except json.JSONDecodeError:
        return None


def set_json_cache(key: str, value: dict[str, Any], user_id: int | None = None) -> None:
    owner_id = resolve_user_id(user_id)
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_cache (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (_scoped_key(key, owner_id), json.dumps(value, ensure_ascii=False, default=str)),
        )
