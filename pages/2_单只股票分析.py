import streamlit as st

from database.db import init_db
from prompts.stock_analysis_prompt import STOCK_ANALYSIS_SYSTEM_PROMPT, build_stock_analysis_prompt
from services.auth_service import require_login
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.indicator_service import analyze_kline
from services.market_data import get_daily_kline
from services.portfolio_service import VALID_MARKETS, list_holdings
from utils.charts import build_kline_figure
from utils.formatters import format_percent


st.set_page_config(page_title="单只股票分析", layout="wide")
init_db()
require_login()

st.title("🔍 单只股票分析")
st.caption("技术指标只用于辅助观察，不构成买入或卖出建议。")

holdings = list_holdings()
holding_options = {"手动输入": None}
holding_options.update({f"{item['stock_name']} ({item['stock_code']})": item for item in holdings})

selected_label = st.selectbox("选择持仓或手动输入", list(holding_options.keys()))
selected = holding_options[selected_label]

col1, col2, col3 = st.columns(3)
default_code = selected["stock_code"] if selected else ""
default_market = selected["market"] if selected else "A股"

stock_code = col1.text_input("股票代码", value=default_code)
market = col2.selectbox(
    "市场",
    VALID_MARKETS,
    index=VALID_MARKETS.index(default_market) if default_market in VALID_MARKETS else 0,
)
days = col3.slider("K线天数", min_value=60, max_value=360, value=180, step=30)
ma_windows = st.multiselect("显示均线", [5, 10, 20, 60], default=[5, 10, 20, 60])

if st.button("开始分析", type="primary"):
    if not stock_code.strip():
        st.error("请输入股票代码")
        st.stop()

    with st.spinner("正在获取日K数据并计算指标..."):
        result = get_daily_kline(stock_code, market, days)

    if not result.ok or result.data is None:
        st.error(result.error or "行情获取失败")
        st.info("如果行情源暂时不可用，可以稍后重试；组合盈亏支持手动价格兜底。")
        st.stop()

    try:
        analyzed, signals = analyze_kline(result.data)
    except Exception as exc:
        st.error(f"技术分析失败：{exc}")
        st.stop()

    st.session_state["single_stock_analysis"] = {
        "stock_code": stock_code,
        "market": market,
        "source": result.source,
        "analyzed": analyzed,
        "signals": signals,
    }

analysis = st.session_state.get("single_stock_analysis")
if analysis:
    analyzed = analysis["analyzed"]
    signals = analysis["signals"]

    st.success(f"行情来源：{analysis['source']}")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("当前价", f"{signals['current_price']:.2f}")
    col_b.metric("MACD", f"{signals['macd']:.4f}" if signals["macd"] is not None else "-")
    col_c.metric("RSI", f"{signals['rsi']:.2f}" if signals["rsi"] is not None else "-")
    col_d.metric("近5日涨幅", format_percent(signals["five_day_return"]))

    st.subheader("📈 K线走势")
    st.caption("红色代表上涨，绿色代表下跌。鼠标悬停可查看同一天的价格、成交量、MACD 和 RSI。")
    st.plotly_chart(
        build_kline_figure(analyzed, ma_windows),
        use_container_width=True,
        config={"displaylogo": False},
    )

    st.subheader("📍 均线位置")
    ma_cols = st.columns(4)
    for idx, (name, is_above) in enumerate(signals["above_ma"].items()):
        ma_cols[idx].metric(name, "上方" if is_above else "下方")

    st.subheader("⚠️ 技术信号")
    signal_rows = [
        ("是否放量上涨", signals["is_volume_up"]),
        ("是否放量下跌", signals["is_volume_down"]),
        ("是否跌破 MA20", signals["breaks_below_ma20"]),
        ("是否跌破 MA60", signals["breaks_below_ma60"]),
        ("是否短期涨幅过大", signals["short_term_gain_too_high"]),
    ]
    for label, value in signal_rows:
        st.write(f"- {label}：{'是' if value else '否'}")

    st.subheader("📝 趋势解释")
    st.write(signals["trend_summary"])
    for note in signals["risk_notes"]:
        st.warning(note)

    with st.expander("查看最近 K 线和指标数据"):
        st.dataframe(analyzed.tail(30), width="stretch", hide_index=True)

    st.divider()
    st.subheader("🧠 AI 通俗解读")
    stock_context = "\n".join(
        [
            f"股票代码：{analysis['stock_code']}",
            f"市场：{analysis['market']}",
            f"当前价：{signals['current_price']}",
            f"MA5：{signals['ma5']}",
            f"MA10：{signals['ma10']}",
            f"MA20：{signals['ma20']}",
            f"MA60：{signals['ma60']}",
            f"MACD：{signals['macd']}",
            f"RSI：{signals['rsi']}",
            f"近5日涨幅：{signals['five_day_return']}",
            f"趋势解释：{signals['trend_summary']}",
            f"风险点：{'；'.join(signals['risk_notes'])}",
        ]
    )
    with st.expander("查看 AI 分析上下文"):
        st.text(stock_context)
    if st.button("生成 AI 解读"):
        client = DeepSeekClient()
        try:
            with st.spinner("DeepSeek 正在生成单股解读..."):
                ai_text = client.generate_text(
                    build_stock_analysis_prompt(stock_context),
                    system_prompt=STOCK_ANALYSIS_SYSTEM_PROMPT,
                )
            st.markdown(ai_text)
        except DeepSeekError as exc:
            st.error(f"AI 调用失败：{exc}")
        except Exception as exc:
            st.error(f"生成失败：{exc}")
