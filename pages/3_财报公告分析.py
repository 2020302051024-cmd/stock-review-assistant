import streamlit as st

from database.db import init_db
from prompts.financial_report_prompt import FINANCIAL_REPORT_SYSTEM_PROMPT, build_financial_report_prompt
from services.auth_service import require_login
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.market_digest_service import (
    build_portfolio_digest_context,
    generate_market_digest,
    get_focus_areas,
    save_focus_areas,
)
from services.news_fetch_service import fetch_digest_sources
from services.report_service import list_ai_reports, save_ai_report
from services.risk_service import scan_financial_text


def _render_risk_scan(risk_scan: dict) -> None:
    text = f"风险等级：{risk_scan['level']}｜命中：{risk_scan['summary']}"
    if risk_scan["level"] == "严重风险":
        st.error(text)
    elif risk_scan["level"] == "风险预警":
        st.warning(text)
    elif risk_scan["level"] == "注意":
        st.info(text)
    else:
        st.success(text)


st.set_page_config(page_title="财报公告分析", layout="wide")
init_db()
require_login()

st.title("📰 财报 / 公告 / 新闻分析")
st.caption("支持单篇摘要，也支持按持仓行业和关注领域生成每日消息面汇总。")

client = DeepSeekClient()

if not client.is_configured():
    st.warning("尚未配置 DeepSeek API Key，请到“系统设置”页面填写。")

tab_single, tab_digest, tab_history = st.tabs(["单篇摘要", "每日消息汇总", "历史记录"])

with tab_single:
    title = st.text_input("标题", placeholder="例如：某公司 2026 年中报摘要")
    source_text = st.text_area("粘贴财报、公告或新闻文本", height=280)

    if st.button("生成摘要", type="primary"):
        if not source_text.strip():
            st.error("请先粘贴需要分析的文本。")
            st.stop()

        risk_scan = scan_financial_text(source_text)
        st.subheader("🚨 暴雷关键词扫描")
        _render_risk_scan(risk_scan)

        try:
            with st.spinner("DeepSeek 正在生成摘要..."):
                result = client.generate_text(
                    build_financial_report_prompt(source_text),
                    system_prompt=FINANCIAL_REPORT_SYSTEM_PROMPT,
                    temperature=0.15,
                )
            st.subheader("🧠 AI 摘要")
            st.markdown(result)
            saved_result = f"关键词风险等级：{risk_scan['level']}\n命中关键词：{risk_scan['summary']}\n\n{result}"
            report_id = save_ai_report("financial_report", title or "财报公告分析", source_text, saved_result)
            st.success(f"已保存分析结果，报告 ID：{report_id}")
        except DeepSeekError as exc:
            st.error(f"AI 调用失败：{exc}")
        except Exception as exc:
            st.error(f"生成失败：{exc}")

with tab_digest:
    st.subheader("🗞️ 每日消息面汇总")
    st.caption("用于每天把持仓股票、所属行业、关注领域和当天材料合成一份汇总报告。")

    portfolio_context = build_portfolio_digest_context()
    with st.expander("当前持仓和关注对象"):
        st.text(portfolio_context)

    focus_areas = st.text_area(
        "关注领域",
        value=get_focus_areas(),
        height=120,
        placeholder="例如：新能源、储能、动力电池、银行、白酒、AI算力、半导体设备等。每行一个也可以。",
    )
    if st.button("保存关注领域"):
        save_focus_areas(focus_areas)
        st.success("关注领域已保存。")

    col_fetch, col_clear = st.columns(2)
    if col_fetch.button("自动抓取持仓新闻 / 公告"):
        with st.spinner("正在自动抓取持仓新闻和公告..."):
            fetched_text, fetch_errors = fetch_digest_sources(max_items_per_stock=5, timeout_seconds=12)
        st.session_state["digest_auto_source"] = fetched_text
        st.session_state["digest_fetch_errors"] = fetch_errors
        if fetched_text:
            st.success("自动抓取完成。抓取结果已加入当天材料。")
        else:
            st.warning("未抓取到可用材料。可以查看错误原因，或手动粘贴材料。")
    if col_clear.button("清空自动抓取材料"):
        st.session_state["digest_auto_source"] = ""
        st.session_state["digest_fetch_errors"] = []
        st.success("已清空自动抓取材料。")

    auto_source = st.session_state.get("digest_auto_source", "")
    fetch_errors = st.session_state.get("digest_fetch_errors", [])
    if auto_source:
        with st.expander("查看自动抓取材料", expanded=False):
            st.text(auto_source)
    if fetch_errors:
        with st.expander("自动抓取失败原因", expanded=False):
            for error in fetch_errors:
                st.write(f"- {error}")

    digest_source = st.text_area(
        "手动补充今天的新闻 / 公告 / 财报材料",
        height=300,
        placeholder="可以一次粘贴多条材料。系统会和自动抓取材料合并分析。",
    )

    if st.button("生成每日消息汇总", type="primary"):
        try:
            combined_source = "\n\n".join(part for part in [auto_source, digest_source] if part.strip())
            with st.spinner("DeepSeek 正在生成每日消息面汇总..."):
                report_id, result, _ = generate_market_digest(combined_source, focus_areas)
            st.success(f"已保存每日消息汇总，报告 ID：{report_id}")
            st.markdown(result)
        except DeepSeekError as exc:
            st.error(f"AI 调用失败：{exc}")
        except Exception as exc:
            st.error(f"生成失败：{exc}")

with tab_history:
    st.subheader("📚 历史摘要")
    reports = list_ai_reports("financial_report", limit=10)
    if not reports:
        st.info("暂无单篇摘要。")
    else:
        for report in reports:
            with st.expander(f"{report['created_at']} - {report['title']}"):
                st.markdown(report["ai_result"])

    st.subheader("📦 历史每日消息汇总")
    digest_reports = list_ai_reports("market_digest", limit=10)
    if not digest_reports:
        st.info("暂无每日消息汇总。")
    else:
        for report in digest_reports:
            with st.expander(f"{report['created_at']} - {report['title']}"):
                st.markdown(report["ai_result"])
