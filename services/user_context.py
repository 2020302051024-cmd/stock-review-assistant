from __future__ import annotations

from typing import Any

import streamlit as st

from database.db import db_connection


def session_user() -> dict[str, Any] | None:
    """Return the signed-in user when running inside Streamlit."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is None:
            return None
        return st.session_state.get("auth_user")
    except Exception:
        return None


def primary_user_id() -> int | None:
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id FROM app_users WHERE is_active = 1 ORDER BY id ASC LIMIT 1"
        ).fetchone()
    return int(row["id"]) if row else None


def resolve_user_id(user_id: int | None = None) -> int:
    """Resolve web requests from session and background scripts from the owner account."""
    if user_id is not None:
        return int(user_id)
    user = session_user()
    if user and user.get("id") is not None:
        return int(user["id"])
    fallback = primary_user_id()
    if fallback is None:
        raise ValueError("尚未创建用户账号，无法保存用户数据")
    return fallback
