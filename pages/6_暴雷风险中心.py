from __future__ import annotations

import pandas as pd
import streamlit as st

from database.db import init_db
from services.auth_service import require_login
from services.cache_service import get_json_cache, set_json_cache
from services.dashboard_service import build_dashboard_snapshot
from services.portfolio_service import list_holdings
from services.risk_service import RISK_LEVELS, risk_items_to_markdown, scan_financial_text
from utils.formatters import format_money, format_percent
from utils.ui import apply_app_style, render_data_freshness, render_page_header


RISK_CENTER_CACHE_KEY = "risk_center_snapshot"


def _render_risk_overview(summary: dict, risk_result: dict, data_status: dict | None = None) -> None:
    level = risk_result.get("overall_level", "正常")
    items = risk_result.get("items", [])
    severe_count = sum(1 for item in items if item.get("level") == "严重风险")
    warning_count = sum(1 for item in items if item.get("level") == "风险预警")

    data_status = data_status or {}
    coverage = f"{data_status.get('valid_prices', 0)}/{data_status.get('total', 0)}"
    cols = st.columns(6)
    cols[0].metric("总体风险", level)
    cols[1].metric("严重风险", severe_count)
    cols[2].metric("风险预警", warning_count)
    cols[3].metric("总浮动盈亏", format_money(summary.get("total_floating_pnl")))
    cols[4].metric("总收益率", format_percent(summary.get("total_return_rate")))
    cols[5].metric("有效行情", coverage)

    if level == "严重风险":
        st.error("存在严重风险信号，请优先核实公告、K线和仓位暴露，不要情绪化操作。")
    elif level == "风险预警":
        st.warning("存在风险预警信号，建议先确认依据，再决定是否调整观察策略。")
    elif level == "注意":
        st.info("存在需要关注的信号，但暂未达到高风险级别。")
    else:
        st.success("暂无明显规则风险。仍需继续关注公告、财报和行情变化。")


def _render_data_status(data_status: dict) -> None:
    total = int(data_status.get("total", 0))
    valid = int(data_status.get("valid_prices", 0))
    cached = int(data_status.get("cached_prices", 0))
    if total == 0:
        return
    if valid == total and cached == 0:
        st.success(f"{valid} 只持仓均已取得有效行情。")
    elif valid == total:
        st.info(f"{valid} 只持仓均有价格，其中 {cached} 只使用最近缓存；请留意数据时间。")
    elif valid > 0:
        st.warning(f"仅 {valid}/{total} 只持仓取得价格，其余股票不参与实时盈亏判断。")
    else:
        st.error("本次没有取得有效价格。请查看数据提示、使用缓存或手动填写当前价。")


def _render_risk_table(risk_result: dict) -> None:
    st.subheader("风险明细")
    items = risk_result.get("items", [])
    if not items:
        st.write("暂无明显风险条目。")
        return

    df = pd.DataFrame(items)
    col_level, col_category = st.columns(2)
    selected_levels = col_level.multiselect("筛选风险等级", RISK_LEVELS, default=RISK_LEVELS)
    categories = sorted(df["category"].dropna().unique().tolist())
    selected_categories = col_category.multiselect("筛选风险类型", categories, default=categories)
    filtered = df[df["level"].isin(selected_levels) & df["category"].isin(selected_categories)]
    st.dataframe(filtered, width="stretch", hide_index=True)


def _render_industry_table(industry_summary: list[dict]) -> None:
    st.subheader("行业集中度")
    if not industry_summary:
        st.write("暂无行业数据。请在持仓管理中补充所属行业。")
        return
    df = pd.DataFrame(industry_summary)
    df["金额"] = df["value"].map(lambda value: format_money(value))
    df["占比"] = df["ratio"].map(lambda value: format_percent(value))
    st.dataframe(df[["industry", "金额", "占比"]], width="stretch", hide_index=True)


def _render_data_warnings(warnings: list[str], price_errors: list[str]) -> None:
    all_warnings = list(warnings or []) + list(price_errors or [])
    if not all_warnings:
        return
    with st.expander("数据不足或行情获取提示", expanded=True):
        for warning in all_warnings:
            st.write(f"- {warning}")


def _render_pnl_rows(pnl_rows: list[dict]) -> None:
    st.subheader("持仓盈亏与价格来源")
    if not pnl_rows:
        st.write("暂无盈亏数据。")
        return
    df = pd.DataFrame(pnl_rows)
    columns = [
        "stock_code",
        "stock_name",
        "industry",
        "buy_price",
        "quantity",
        "current_price",
        "market_value",
        "floating_pnl",
        "return_rate",
        "price_source",
    ]
    safe_columns = [column for column in columns if column in df.columns]
    st.dataframe(df[safe_columns], width="stretch", hide_index=True)


def _render_scan_tab(holdings: list[dict]) -> None:
    st.subheader("规则风险扫描")
    st.caption("腾讯日 K 优先，新浪和东方财富备用；同一次扫描不会重复请求同一只股票。")

    if st.session_state.get("risk_center_refresh_message"):
        st.success(st.session_state.pop("risk_center_refresh_message"))

    cache = get_json_cache(RISK_CENTER_CACHE_KEY)
    if cache:
        snapshot = cache["value"]
        risk_result = snapshot["risk_result"]
        summary = snapshot["summary"]
        pnl_rows = snapshot["pnl_rows"]
        data_status = snapshot.get("data_status", {})

        render_data_freshness(cache["updated_at"], "风险扫描更新时间")
        _render_data_status(data_status)
        _render_risk_overview(summary, risk_result, data_status)
        _render_risk_table(risk_result)
        _render_industry_table(risk_result.get("industry_summary", []))
        _render_data_warnings(risk_result.get("warnings", []), summary.get("errors", []))
        _render_pnl_rows(pnl_rows)

        with st.expander("复制给 DeepSeek / 微信推送的风险摘要"):
            st.markdown(risk_items_to_markdown(risk_result))
    else:
        st.info("暂无风险扫描结果。展开下方设置并执行第一次扫描。")

    with st.expander("更新扫描设置", expanded=not bool(cache)):
        with st.form("risk_center_scan_form"):
            col_a, col_b, col_c = st.columns(3)
            fetch_market_price = col_a.checkbox("获取最新日线行情", value=True)
            include_kline = col_b.checkbox("检查 K线风险", value=True)
            total_assets = col_c.number_input(
                "账户总资产，可选",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                help="填写后可判断总股票仓位是否超过阈值。",
            )

            manual_prices: dict[int, float] = {}
            with st.expander("行情失败时手动填写当前价"):
                for holding in holdings:
                    value = st.number_input(
                        f"{holding['stock_name']} ({holding['stock_code']}) 当前价",
                        min_value=0.0,
                        value=0.0,
                        step=0.01,
                        key=f"risk_center_manual_price_{holding['id']}",
                    )
                    if value > 0:
                        manual_prices[int(holding["id"])] = value
            submitted = st.form_submit_button("更新风险扫描", type="primary")

        if submitted:
            with st.spinner("正在并发获取持仓行情并计算风险..."):
                snapshot = build_dashboard_snapshot(
                    manual_prices=manual_prices,
                    fetch_market_price=fetch_market_price,
                    include_kline=include_kline,
                    total_assets=total_assets if total_assets > 0 else None,
                )
                set_json_cache(RISK_CENTER_CACHE_KEY, snapshot)
            st.session_state["risk_center_refresh_message"] = "风险扫描已更新。"
            st.rerun()


def _render_text_scan_tab(holdings: list[dict]) -> None:
    st.subheader("财报 / 公告 / 新闻暴雷关键词扫描")
    st.caption("先做本地关键词扫描，不调用 AI，适合快速判断公告里是否有明显风险词。")
    stock_options = {"不指定股票": None}
    stock_options.update({f"{item['stock_name']} ({item['stock_code']})": item for item in holdings})
    selected_label = st.selectbox("关联持仓，可选", list(stock_options.keys()))
    text = st.text_area(
        "粘贴财报、公告或新闻文本",
        height=240,
        placeholder="例如：业绩预告、监管问询、减持公告、诉讼公告等。",
    )
    if not st.button("扫描文本风险"):
        return
    if not text.strip():
        st.error("请先粘贴文本。")
        return

    result = scan_financial_text(text)
    selected = stock_options[selected_label]
    target = f"{selected['stock_name']}({selected['stock_code']})" if selected else "未指定股票"
    st.metric("文本风险等级", result["level"])
    if result["level"] in {"严重风险", "风险预警"}:
        st.error(f"{target} 命中风险词：{result['summary']}")
    elif result["level"] == "注意":
        st.warning(f"{target} 命中关注词：{result['summary']}")
    else:
        st.success(f"{target}：未命中明显暴雷关键词。")
    with st.expander("命中关键词明细"):
        st.write(result["matched_keywords"] or "无")


def main() -> None:
    st.set_page_config(page_title="暴雷风险中心", layout="wide")
    apply_app_style(page_tone="danger")
    init_db()
    require_login()

    render_page_header(
        "暴雷风险中心",
        "集中检查仓位、行业集中度、K线和公告文本风险，只提供风险依据。",
        "!",
        tone="danger",
    )

    holdings = list_holdings()
    if not holdings:
        st.info("暂无持仓，请先到“持仓管理”页面录入持仓。")
        return

    tab_scan, tab_text = st.tabs(["持仓风险扫描", "财报/公告文本扫描"])
    with tab_scan:
        _render_scan_tab(holdings)
    with tab_text:
        _render_text_scan_tab(holdings)


if __name__ == "__main__":
    main()
