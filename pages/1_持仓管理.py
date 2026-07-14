from __future__ import annotations

from io import BytesIO
from datetime import date

import pandas as pd
import streamlit as st

from database.db import init_db
from services.auth_service import require_login
from services.portfolio_service import (
    VALID_MARKETS,
    add_holding,
    batch_add_holdings,
    build_import_template_dataframe,
    delete_holding,
    get_holding,
    holdings_dataframe,
    list_holdings,
    normalize_import_dataframe,
    update_holding,
)


st.set_page_config(page_title="持仓管理", layout="wide")
init_db()
require_login()

st.title("🗂️ 持仓管理")
st.caption("维护你的股票持仓。这里不连接券商账户，也不会执行交易。")

if "add_form_version" not in st.session_state:
    st.session_state["add_form_version"] = 0

if st.session_state.get("add_success_message"):
    st.success(st.session_state.pop("add_success_message"))


def holding_form(prefix: str, initial: dict | None = None) -> dict:
    initial = initial or {}
    col1, col2, col3 = st.columns(3)
    stock_code = col1.text_input("股票代码", value=initial.get("stock_code", ""), key=f"{prefix}_code")
    stock_name = col2.text_input("股票名称", value=initial.get("stock_name", ""), key=f"{prefix}_name")
    market = col3.selectbox(
        "所属市场",
        VALID_MARKETS,
        index=VALID_MARKETS.index(initial.get("market", "A股")) if initial.get("market", "A股") in VALID_MARKETS else 0,
        key=f"{prefix}_market",
    )

    col4, col5, col6 = st.columns(3)
    buy_price = col4.number_input(
        "买入价格",
        min_value=0.0,
        value=float(initial.get("buy_price", 0.0)),
        step=0.01,
        key=f"{prefix}_price",
    )
    quantity = col5.number_input(
        "持仓数量",
        min_value=0,
        value=int(initial.get("quantity", 0)),
        step=100,
        key=f"{prefix}_qty",
    )
    raw_buy_date = initial.get("buy_date")
    default_date = date.fromisoformat(raw_buy_date) if raw_buy_date else date.today()
    buy_date = col6.date_input("买入日期", value=default_date, key=f"{prefix}_date")
    col7, col8 = st.columns([1, 1])
    industry = col7.text_input("所属行业", value=initial.get("industry", ""), key=f"{prefix}_industry")
    is_watchlist = col8.checkbox(
        "重点监控",
        value=bool(initial.get("is_watchlist", 0)),
        key=f"{prefix}_watchlist",
    )
    investment_logic = st.text_area(
        "投资逻辑",
        value=initial.get("investment_logic", ""),
        key=f"{prefix}_logic",
        placeholder="例如：看好行业景气度、低估值修复、业绩增长等。",
    )
    note = st.text_area("备注", value=initial.get("note", ""), key=f"{prefix}_note")

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


def read_uploaded_holdings(uploaded_file) -> pd.DataFrame:
    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        content = uploaded_file.getvalue()
        for encoding in ["utf-8-sig", "utf-8", "gbk"]:
            try:
                return pd.read_csv(BytesIO(content), encoding=encoding, dtype={"股票代码": str, "stock_code": str})
            except UnicodeDecodeError:
                continue
        raise ValueError("CSV 编码无法识别，请另存为 UTF-8 或使用模板重新填写。")
    if filename.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(uploaded_file, dtype={"股票代码": str, "stock_code": str})
    raise ValueError("仅支持 CSV、XLSX 或 XLSM 文件。")


def build_excel_template_bytes(template_df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template_df.to_excel(writer, index=False, sheet_name="持仓导入模板")
    return output.getvalue()


tab_add, tab_import, tab_edit, tab_delete, tab_list = st.tabs(["新增", "批量导入", "修改", "删除", "查看"])

with tab_add:
    with st.form("add_holding_form"):
        payload = holding_form(f"add_{st.session_state['add_form_version']}")
        submitted = st.form_submit_button("新增持仓")
    if submitted:
        try:
            holding_id = add_holding(payload)
            st.session_state["add_success_message"] = f"新增成功，持仓 ID：{holding_id}"
            st.session_state["add_form_version"] += 1
            st.rerun()
        except Exception as exc:
            st.error(f"新增失败：{exc}")

with tab_import:
    st.subheader("📥 表格批量导入")
    st.caption("适合一次录入多只股票。导入只写入本系统数据库，不会连接券商或执行交易。")

    template_df = build_import_template_dataframe()
    col_tpl1, col_tpl2 = st.columns(2)
    col_tpl1.download_button(
        "下载 Excel 模板",
        data=build_excel_template_bytes(template_df),
        file_name="stock_holdings_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    col_tpl2.download_button(
        "下载 CSV 模板",
        data=template_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="stock_holdings_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    with st.expander("模板字段说明", expanded=False):
        st.write(
            "- 必填：股票代码、股票名称、买入价格、持仓数量、买入日期。\n"
            "- 可选：所属市场、所属行业、投资逻辑、重点监控、备注。\n"
            "- 所属市场为空时默认 A股；重点监控可填 是/否、1/0、true/false。\n"
            "- 同一股票可以导入多行，用于记录不同买入批次。"
        )
        st.dataframe(template_df, width="stretch", hide_index=True)

    uploaded_file = st.file_uploader("上传填写好的持仓表格", type=["csv", "xlsx", "xlsm"])
    if uploaded_file is not None:
        try:
            raw_df = read_uploaded_holdings(uploaded_file)
            preview_df = normalize_import_dataframe(raw_df)
            st.success(f"已识别 {len(preview_df)} 行待导入数据。")
            st.dataframe(preview_df, width="stretch", hide_index=True)
            if st.button("确认导入这些持仓", type="primary"):
                result = batch_add_holdings(raw_df)
                success_count = len(result["successes"])
                error_count = len(result["errors"])
                if success_count:
                    st.success(f"成功导入 {success_count} 条持仓。")
                if error_count:
                    st.warning(f"{error_count} 行导入失败，请按错误提示修改后重新导入。")
                    st.dataframe(pd.DataFrame(result["errors"]), width="stretch", hide_index=True)
        except Exception as exc:
            st.error(f"表格读取或校验失败：{exc}")

with tab_edit:
    holdings = list_holdings()
    if not holdings:
        st.info("暂无持仓可修改。")
    else:
        options = {f"{item['stock_name']} ({item['stock_code']}) - ID {item['id']}": item["id"] for item in holdings}
        selected_label = st.selectbox("选择要修改的持仓", list(options.keys()))
        selected = get_holding(options[selected_label])
        with st.form("edit_holding_form"):
            payload = holding_form("edit", selected)
            submitted = st.form_submit_button("保存修改")
        if submitted:
            try:
                update_holding(options[selected_label], payload)
                st.success("修改成功")
            except Exception as exc:
                st.error(f"修改失败：{exc}")

with tab_delete:
    holdings = list_holdings()
    if not holdings:
        st.info("暂无持仓可删除。")
    else:
        options = {f"{item['stock_name']} ({item['stock_code']}) - ID {item['id']}": item["id"] for item in holdings}
        selected_label = st.selectbox("选择要删除的持仓", list(options.keys()), key="delete_select")
        st.warning("删除后不可在页面中撤销，请确认这只是删除本地记录，不影响真实账户。")
        if st.button("确认删除"):
            try:
                delete_holding(options[selected_label])
                st.success("删除成功")
            except Exception as exc:
                st.error(f"删除失败：{exc}")

with tab_list:
    df = holdings_dataframe()
    if df.empty:
        st.info("暂无持仓。")
    else:
        st.dataframe(df, width="stretch", hide_index=True)
