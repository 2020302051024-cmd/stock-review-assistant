from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import streamlit as st

from database.db import db_connection


PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return digest, salt


def has_users() -> bool:
    with db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM app_users").fetchone()
    return int(row["count"]) > 0


def create_user(username: str, password: str) -> int:
    username = username.strip()
    if not username:
        raise ValueError("用户名不能为空")
    if len(password) < 6:
        raise ValueError("密码至少 6 位")
    password_hash, salt = hash_password(password)
    with db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO app_users (username, password_hash, salt)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, salt),
        )
        return int(cursor.lastrowid)


def list_users() -> list[dict[str, Any]]:
    with db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, username, is_active, created_at, updated_at
            FROM app_users
            ORDER BY created_at ASC, id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, salt, is_active
            FROM app_users
            WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()
    if not row or not int(row["is_active"]):
        return None
    candidate_hash, _ = hash_password(password, row["salt"])
    if not hmac.compare_digest(candidate_hash, row["password_hash"]):
        return None
    return {"id": int(row["id"]), "username": row["username"]}


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("auth_user")


def logout() -> None:
    st.session_state.pop("auth_user", None)


def require_login() -> dict[str, Any]:
    user = current_user()
    if user:
        with st.sidebar:
            st.markdown(
                """
                <div class="app-brand">
                  <div class="app-brand-mark">复盘</div>
                  <div>
                    <div class="app-brand-name">股票复盘助手</div>
                    <div class="app-brand-note">个人风险与复盘工作台</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.page_link("app.py", label="风险仪表盘", icon="🏠")
            st.page_link("pages/6_暴雷风险中心.py", label="暴雷风险中心", icon="🚨")
            st.page_link("pages/1_持仓管理.py", label="持仓管理", icon="📁")
            st.page_link("pages/2_单只股票分析.py", label="单股分析", icon="📈")
            st.page_link("pages/3_财报公告分析.py", label="财报与消息", icon="📰")
            st.page_link("pages/4_每日复盘报告.py", label="每日复盘", icon="📋")
            st.page_link("pages/7_交易日志.py", label="交易日志", icon="✍️")
            st.page_link("pages/5_系统设置.py", label="系统设置", icon="⚙️")
            st.divider()
            st.caption(f"已登录：{user['username']}")
            if st.button("退出登录", key="sidebar_logout", use_container_width=True):
                logout()
                st.rerun()
        return user

    if not has_users():
        _render_first_user_setup()
    else:
        _render_login_form()
    st.stop()


def _render_first_user_setup() -> None:
    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        st.markdown("## 创建第一个账号")
        st.caption("该账号的数据、API 和推送配置将与后续账号相互隔离。")
        with st.form("first_user_setup"):
            username = st.text_input("用户名", value="admin")
            password = st.text_input("密码", type="password")
            confirm = st.text_input("确认密码", type="password")
            submitted = st.form_submit_button("创建账号", type="primary", use_container_width=True)
    if submitted:
        if password != confirm:
            st.error("两次密码不一致")
            return
        try:
            create_user(username, password)
            st.success("管理员账号已创建，请登录。")
            st.rerun()
        except Exception as exc:
            st.error(f"创建失败：{exc}")


def _render_login_form() -> None:
    _, center, _ = st.columns([1, 1.05, 1])
    with center:
        st.markdown("## 股票复盘助手")
        st.caption("登录后查看你的持仓、风险扫描、报告与交易日志。")
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
    if submitted:
        user = authenticate_user(username, password)
        if not user:
            st.error("用户名或密码错误")
            return
        st.session_state["auth_user"] = user
        st.rerun()
