from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from database.db import init_db
from services.auth_service import require_login
from services.portfolio_service import list_holdings
from services.trade_log_service import (
    EMOTION_OPTIONS,
    TRADE_ACTIONS,
    add_trade_log,
    delete_trade_log,
    get_trade_log,
    list_trade_logs,
    trade_log_summary,
    update_trade_log,
)
from utils.formatters import format_money
from utils.ui import apply_app_style, render_page_header


def _stock_fields(prefix: str, holdings: list[dict], initial: dict | None = None) -> dict:
    initial = initial or {}
    options = {"手动填写": None}
    options.update({f"{item['stock_name']} ({item['stock_code']})": item for item in holdings})
    default_label = "手动填写"
    if initial.get("holding_id"):
        for label, item in options.items():
            if item and int(item["id"]) == int(initial["holding_id"]):
                default_label = label
                break
    selected_label = st.selectbox(
        "关联持仓",
        list(options.keys()),
        index=list(options.keys()).index(default_label),
        key=f"{prefix}_holding",
    )
    selected = options[selected_label]
    col_code, col_name = st.columns(2)
    stock_code = col_code.text_input(
        "股票代码",
        value=selected["stock_code"] if selected else initial.get("stock_code", ""),
        disabled=selected is not None,
        key=f"{prefix}_code",
    )
    stock_name = col_name.text_input(
        "股票名称",
        value=selected["stock_name"] if selected else initial.get("stock_name", ""),
        disabled=selected is not None,
        key=f"{prefix}_name",
    )
    return {
        "holding_id": selected["id"] if selected else initial.get("holding_id"),
        "stock_code": selected["stock_code"] if selected else stock_code,
        "stock_name": selected["stock_name"] if selected else stock_name,
    }


def _log_form(prefix: str, holdings: list[dict], initial: dict | None = None) -> dict:
    initial = initial or {}
    payload = _stock_fields(prefix, holdings, initial)
    col_action, col_date, col_emotion = st.columns(3)
    action = col_action.selectbox(
        "记录类型",
        TRADE_ACTIONS,
        index=TRADE_ACTIONS.index(initial.get("action", "观察")) if initial.get("action", "观察") in TRADE_ACTIONS else 0,
        key=f"{prefix}_action",
    )
    raw_date = initial.get("trade_date")
    trade_date = col_date.date_input(
        "日期",
        value=date.fromisoformat(raw_date) if raw_date else date.today(),
        key=f"{prefix}_date",
    )
    emotion = col_emotion.selectbox(
        "当时情绪",
        EMOTION_OPTIONS,
        index=EMOTION_OPTIONS.index(initial.get("emotion", "平静")) if initial.get("emotion", "平静") in EMOTION_OPTIONS else 0,
        key=f"{prefix}_emotion",
    )
    col_price, col_quantity = st.columns(2)
    price = col_price.number_input(
        "成交/观察价格",
        min_value=0.0,
        value=float(initial.get("price", 0.0)),
        step=0.01,
        key=f"{prefix}_price",
    )
    quantity = col_quantity.number_input(
        "数量",
        min_value=0,
        value=int(initial.get("quantity", 0)),
        step=100,
        key=f"{prefix}_quantity",
    )
    reason = st.text_area(
        "当时的理由",
        value=initial.get("reason", ""),
        placeholder="记录事实和依据，例如业绩变化、估值、仓位或技术信号。",
        key=f"{prefix}_reason",
    )
    discipline_note = st.text_area(
        "纪律复盘",
        value=initial.get("discipline_note", ""),
        placeholder="是否按计划执行？有哪些冲动或遗漏？下一次如何改进？",
        key=f"{prefix}_discipline",
    )
    payload.update(
        {
            "action": action,
            "trade_date": trade_date,
            "emotion": emotion,
            "price": price,
            "quantity": quantity,
            "reason": reason,
            "discipline_note": discipline_note,
        }
    )
    return payload


def main() -> None:
    st.set_page_config(page_title="交易日志", page_icon="📝", layout="wide")
    apply_app_style()
    init_db()
    require_login()

    render_page_header("交易日志", "记录真实操作、当时理由和情绪，用事实检查交易纪律。", "✎")

    holdings = list_holdings()
    logs = list_trade_logs()
    summary = trade_log_summary(logs)
    cols = st.columns(4)
    cols[0].metric("日志总数", summary["count"])
    cols[1].metric("实际交易记录", summary["trade_count"])
    cols[2].metric("记录成交额", format_money(summary["total_amount"]))
    cols[3].metric("冲动/贪心记录", summary["impulsive_count"])

    tab_add, tab_history, tab_edit = st.tabs(["新增记录", "日志明细", "修改与删除"])
    with tab_add:
        with st.form("add_trade_log_form", clear_on_submit=True):
            payload = _log_form("add_log", holdings)
            submitted = st.form_submit_button("保存日志", type="primary")
        if submitted:
            try:
                log_id = add_trade_log(payload)
                st.success(f"交易日志已保存，ID：{log_id}")
                st.rerun()
            except Exception as exc:
                st.error(f"保存失败：{exc}")

    with tab_history:
        if not logs:
            st.info("还没有交易日志。")
        else:
            frame = pd.DataFrame(logs)
            actions = ["全部"] + TRADE_ACTIONS
            selected_action = st.selectbox("筛选记录类型", actions)
            if selected_action != "全部":
                frame = frame[frame["action"] == selected_action]
            display_columns = [
                "trade_date", "stock_code", "stock_name", "action", "price", "quantity",
                "amount", "emotion", "reason", "discipline_note",
            ]
            st.dataframe(frame[display_columns], width="stretch", hide_index=True)

    with tab_edit:
        if not logs:
            st.info("暂无日志可修改。")
        else:
            options = {
                f"{item['trade_date']}｜{item['stock_name']}｜{item['action']}｜ID {item['id']}": item["id"]
                for item in logs
            }
            selected_label = st.selectbox("选择日志", list(options.keys()))
            selected = get_trade_log(options[selected_label])
            with st.form("edit_trade_log_form"):
                edit_payload = _log_form("edit_log", holdings, selected)
                col_save, col_delete = st.columns(2)
                save_clicked = col_save.form_submit_button("保存修改", type="primary")
                delete_clicked = col_delete.form_submit_button("删除记录")
            try:
                if save_clicked:
                    update_trade_log(options[selected_label], edit_payload)
                    st.success("日志已更新。")
                    st.rerun()
                if delete_clicked:
                    delete_trade_log(options[selected_label])
                    st.success("日志已删除。")
                    st.rerun()
            except Exception as exc:
                st.error(f"操作失败：{exc}")


if __name__ == "__main__":
    main()
