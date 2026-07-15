import pandas as pd
import streamlit as st

from config import settings
from database.db import init_db
from prompts.daily_review_prompt import DAILY_REVIEW_SYSTEM_PROMPT
from services.auth_service import require_login
from services.cache_service import get_json_cache, set_json_cache
from services.dashboard_service import build_dashboard_snapshot
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.portfolio_service import list_holdings
from services.push_service import PushError, send_wechat_push
from services.risk_service import risk_items_to_markdown
from utils.formatters import format_money, format_percent
from utils.ui import apply_app_style, render_data_freshness, render_page_header


DASHBOARD_CACHE_KEY = "dashboard_snapshot"

st.set_page_config(page_title="风险仪表盘", page_icon="📊", layout="wide")


def main() -> None:
    init_db()
    require_login()

    render_page_header("风险仪表盘", "先看风险，再看盈亏。首页读取最近缓存，不会在打开时重复请求行情。", "⌂")
    if st.session_state.get("dashboard_refresh_message"):
        st.success(st.session_state.pop("dashboard_refresh_message"))

    holdings = list_holdings()
    if not holdings:
        st.info("还没有录入持仓。请先到“持仓管理”页面新增你的第一只股票。")
        return

    cache = get_json_cache(DASHBOARD_CACHE_KEY)
    if cache:
        render_data_freshness(cache["updated_at"])
        snapshot = cache["value"]
        summary = snapshot["summary"]
        risk_result = snapshot["risk_result"]
        pnl_rows = snapshot["pnl_rows"]

        _render_summary(summary, risk_result)
        _render_risk_items(risk_result.get("items", []))
        _render_industry_summary(risk_result.get("industry_summary", []))
        _render_warnings(risk_result.get("warnings", []))
        _render_actions(risk_result)
        _render_pnl_table(pnl_rows)
    else:
        st.info("暂无风险快照。展开下方“更新数据”生成第一次扫描。")

    with st.expander("更新数据与手动价格", expanded=not bool(cache)):
        col_a, col_b = st.columns(2)
        fetch_market_price = col_a.checkbox("获取当前行情", value=True)
        include_kline = col_b.checkbox("检查 K线风险", value=True)
        total_assets = st.number_input(
            "账户总资产，可选",
            min_value=0.0,
            value=0.0,
            step=1000.0,
            help="填写后可判断总股票仓位是否超过 70%。",
        )
        manual_prices = {}
        with st.expander("行情失败时手动填写当前价"):
            for holding in holdings:
                manual_value = st.number_input(
                    f"{holding['stock_name']} ({holding['stock_code']}) 当前价",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    key=f"manual_price_{holding['id']}",
                )
                if manual_value > 0:
                    manual_prices[int(holding["id"])] = manual_value
        if st.button("刷新风险数据", type="primary"):
            with st.spinner("正在拉取行情并计算风险..."):
                snapshot = build_dashboard_snapshot(
                    manual_prices=manual_prices,
                    fetch_market_price=fetch_market_price,
                    include_kline=include_kline,
                    total_assets=total_assets if total_assets > 0 else None,
                )
                set_json_cache(DASHBOARD_CACHE_KEY, snapshot)
            st.session_state["dashboard_refresh_message"] = "风险数据已刷新。"
            st.rerun()


def _render_summary(summary: dict, risk_result: dict) -> None:
    risk_level = risk_result.get("overall_level", "正常")
    metric_cols = st.columns(4)
    metric_cols[0].metric("今日风险等级", risk_level)
    metric_cols[1].metric("总浮动盈亏", format_money(summary.get("total_floating_pnl")))
    metric_cols[2].metric("总收益率", format_percent(summary.get("total_return_rate")))
    metric_cols[3].metric("风险条目", len(risk_result.get("items", [])))

    if risk_level == "严重风险":
        st.error("存在严重风险信号，请优先查看原因，避免情绪化操作。")
    elif risk_level == "风险预警":
        st.warning("存在风险预警信号，建议谨慎观察并控制仓位。")
    elif risk_level == "注意":
        st.info("存在需要注意的信号，暂未达到高风险级别。")
    else:
        st.success("暂无明显暴雷、K线或仓位风险。")


def _render_risk_items(items: list[dict[str, str]]) -> None:
    st.subheader("⚠️ 风险明细")
    if not items:
        st.write("暂无明显风险条目。")
        return

    for item in items:
        label = f"{item['level']}｜{item['category']}｜{item['stock_name']}({item['stock_code']})"
        if item["level"] == "严重风险":
            st.error(f"{label}\n\n{item['reason']}。依据：{item['evidence']}")
        elif item["level"] == "风险预警":
            st.warning(f"{label}\n\n{item['reason']}。依据：{item['evidence']}")
        else:
            st.info(f"{label}\n\n{item['reason']}。依据：{item['evidence']}")


def _render_industry_summary(industry_summary: list[dict]) -> None:
    st.subheader("🏭 行业集中度")
    if not industry_summary:
        st.write("暂无行业数据。请在持仓管理中补充所属行业。")
        return
    for item in industry_summary[:5]:
        st.write(f"- {item['industry']}：{format_money(item['value'])}，占比 {format_percent(item['ratio'])}")


def _render_warnings(warnings: list[str]) -> None:
    if warnings:
        with st.expander("数据不足或行情获取提示"):
            for warning in warnings:
                st.write(f"- {warning}")


def _render_actions(risk_result: dict) -> None:
    push_content = risk_items_to_markdown(risk_result)
    push_cols = st.columns(2)
    if push_cols[0].button("📤 推送风险摘要到微信"):
        try:
            message = send_wechat_push("股票复盘助手：风险摘要", push_content)
            st.success(message)
        except PushError as exc:
            st.error(f"推送失败：{exc}")
        except Exception as exc:
            st.error(f"推送异常：{exc}")

    if push_cols[1].button("🧠 DeepSeek 一句话风险总结"):
        client = DeepSeekClient()
        prompt = (
            "请用一句中文总结今天的股票账户风险，必须严格、简洁，"
            "不要给买入或卖出指令，只能给观察和风险控制提醒。\n\n"
            f"{push_content}"
        )
        try:
            with st.spinner("DeepSeek 正在生成一句话风险总结..."):
                text = client.generate_text(prompt, system_prompt=DAILY_REVIEW_SYSTEM_PROMPT, temperature=0.2)
            st.info(text)
        except DeepSeekError as exc:
            st.error(f"AI 调用失败：{exc}")
        except Exception as exc:
            st.error(f"生成失败：{exc}")


def _render_pnl_table(pnl_rows: list[dict]) -> None:
    st.divider()
    st.subheader("📈 每日盈亏简表")
    if not pnl_rows:
        st.write("暂无盈亏数据。")
        return
    pnl_df = pd.DataFrame(pnl_rows)
    display_columns = [
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
    safe_columns = [col for col in display_columns if col in pnl_df.columns]
    st.dataframe(pnl_df[safe_columns], width="stretch", hide_index=True)


if __name__ == "__main__":
    apply_app_style()
    main()
