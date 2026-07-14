import streamlit as st

from database.db import init_db
from prompts.daily_review_prompt import DAILY_REVIEW_SYSTEM_PROMPT, build_daily_review_qa_prompt
from services.auth_service import require_login
from services.daily_review_service import build_daily_review_context, generate_and_save_daily_review
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.portfolio_service import list_holdings
from services.report_service import list_ai_reports
from utils.formatters import format_money, format_percent


st.set_page_config(page_title="每日复盘报告", layout="wide")
init_db()
require_login()

st.title("📋 每日复盘报告")
st.caption("历史报告优先展示。新报告按需生成，不在打开页面时自动加载行情。")

client = DeepSeekClient()
holdings = list_holdings()

if not holdings:
    st.info("暂无持仓，请先到“持仓管理”页面录入持仓。")
    st.stop()

reports = list_ai_reports("daily_review", limit=30)

st.subheader("📚 历史复盘")
if not reports:
    st.info("暂无历史复盘。你可以在下方生成第一份报告。")
else:
    latest = reports[0]
    st.markdown(f"**最新报告：** {latest['created_at']} - {latest['title']}")
    st.markdown(latest["ai_result"])

    if len(reports) > 1:
        st.markdown("**更早的复盘报告**")
        for report in reports[1:]:
            with st.expander(f"{report['created_at']} - {report['title']}"):
                st.markdown(report["ai_result"])

st.divider()
st.subheader("❓ 向 DeepSeek 追问")
qa_source_options = ["使用最新历史报告", "重新构建当前持仓上下文"]
qa_source = st.radio("回答依据", qa_source_options, horizontal=True)
question = st.text_area(
    "你的问题",
    placeholder="例如：今天最需要警惕哪只股票？为什么？我是否有仓位过重的问题？",
)

if st.button("让 DeepSeek 回答我的问题"):
    if not question.strip():
        st.error("请先输入问题。")
    else:
        try:
            if qa_source == "使用最新历史报告":
                if not reports:
                    st.error("暂无历史报告，请先生成一份复盘或选择重新构建当前持仓上下文。")
                    st.stop()
                context_text = reports[0]["source_text"] or reports[0]["ai_result"]
            else:
                with st.spinner("正在构建当前持仓上下文..."):
                    context_text, _ = build_daily_review_context(fetch_market_price=True, include_technical=True)

            with st.spinner("DeepSeek 正在回答..."):
                answer = client.generate_text(
                    build_daily_review_qa_prompt(context_text, question),
                    system_prompt=DAILY_REVIEW_SYSTEM_PROMPT,
                    temperature=0.15,
                )
            st.markdown(answer)
        except DeepSeekError as exc:
            st.error(f"AI 调用失败：{exc}")
        except Exception as exc:
            st.error(f"回答失败：{exc}")

st.divider()
st.subheader("🧾 生成新复盘")
st.caption("生成新报告会拉取行情和K线，可能需要一些时间。历史报告不受影响。")

fetch_market_price = st.checkbox("自动获取当前行情", value=True)
include_technical = st.checkbox("加入 K线技术摘要", value=True)
manual_prices = {}

with st.expander("手动输入当前价格兜底"):
    for holding in holdings:
        value = st.number_input(
            f"{holding['stock_name']} ({holding['stock_code']}) 当前价",
            min_value=0.0,
            value=0.0,
            step=0.01,
            key=f"review_manual_price_{holding['id']}",
        )
        if value > 0:
            manual_prices[int(holding["id"])] = value

user_notes = st.text_area("今天的补充备注", placeholder="例如：某只股票有公告、自己今天有冲动交易想复盘等。")

if st.button("预览本次复盘上下文"):
    try:
        with st.spinner("正在计算组合表现和技术摘要..."):
            context_text, meta = build_daily_review_context(
                manual_prices=manual_prices,
                fetch_market_price=fetch_market_price,
                include_technical=include_technical,
            )
        summary = meta["summary"]
        col1, col2, col3 = st.columns(3)
        col1.metric("当前市值", format_money(summary["total_market_value"]))
        col2.metric("总浮动盈亏", format_money(summary["total_floating_pnl"]))
        col3.metric("总收益率", format_percent(summary["total_return_rate"]))
        st.text(context_text)
    except Exception as exc:
        st.error(f"预览失败：{exc}")

if st.button("生成并保存每日复盘", type="primary"):
    if not client.is_configured():
        st.error("尚未配置 DeepSeek API Key，请到“系统设置”页面查看配置说明。")
        st.stop()
    try:
        with st.spinner("正在生成并保存每日复盘..."):
            report_id, result, _ = generate_and_save_daily_review(
                notes=user_notes,
                manual_prices=manual_prices,
                fetch_market_price=fetch_market_price,
                include_technical=include_technical,
            )
        st.success(f"已保存复盘报告，报告 ID：{report_id}")
        st.markdown(result)
    except DeepSeekError as exc:
        st.error(f"AI 调用失败：{exc}")
    except Exception as exc:
        st.error(f"生成失败：{exc}")
