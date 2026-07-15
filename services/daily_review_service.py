from __future__ import annotations

from typing import Any

from prompts.daily_review_prompt import DAILY_REVIEW_SYSTEM_PROMPT, build_daily_review_prompt
from services.deepseek_service import DeepSeekClient, DeepSeekError
from services.indicator_service import analyze_kline
from services.market_data import get_daily_kline
from services.portfolio_service import list_holdings
from services.report_service import calculate_portfolio_pnl, portfolio_context_to_text, save_ai_report
from services.risk_service import analyze_portfolio_risks, risk_items_to_markdown
from services.trade_log_service import list_trade_logs, trade_logs_to_context


def build_daily_review_context(
    manual_prices: dict[int, float] | None = None,
    fetch_market_price: bool = True,
    include_technical: bool = True,
) -> tuple[str, dict[str, Any]]:
    holdings = list_holdings()
    pnl_df, summary = calculate_portfolio_pnl(
        holdings,
        manual_prices=manual_prices or {},
        fetch_market_price=fetch_market_price,
    )
    technical_summaries = _build_technical_summaries(holdings) if include_technical else []
    context_text = portfolio_context_to_text(pnl_df, summary, technical_summaries)
    risk_result = analyze_portfolio_risks(pnl_df, total_assets=None, include_kline=False)
    context_text = f"{context_text}\n\n规则风险扫描：\n{risk_items_to_markdown(risk_result)}"
    recent_trade_logs = list_trade_logs(limit=12)
    context_text = f"{context_text}\n\n{trade_logs_to_context(recent_trade_logs)}"
    return context_text, {
        "holdings": holdings,
        "pnl_df": pnl_df,
        "summary": summary,
        "technical_summaries": technical_summaries,
        "risk_result": risk_result,
        "trade_logs": recent_trade_logs,
    }


def generate_and_save_daily_review(
    notes: str = "",
    manual_prices: dict[int, float] | None = None,
    fetch_market_price: bool = True,
    include_technical: bool = True,
    title: str = "每日复盘报告",
) -> tuple[int, str, str]:
    context_text, _ = build_daily_review_context(
        manual_prices=manual_prices,
        fetch_market_price=fetch_market_price,
        include_technical=include_technical,
    )
    client = DeepSeekClient()
    source_text = context_text + "\n\n用户备注：\n" + notes
    try:
        result = client.generate_text(
            build_daily_review_prompt(context_text, notes),
            system_prompt=DAILY_REVIEW_SYSTEM_PROMPT,
            temperature=0.15,
        )
    except DeepSeekError as exc:
        failure_text = (
            "AI 生成失败，已保存本次复盘上下文。\n\n"
            f"失败原因：{exc}\n\n"
            "处理建议：稍后重试；或在系统设置里调高 AI 超时秒数、降低推理强度、"
            "临时切换 deepseek-chat；也可以减少持仓/K线内容后再生成。"
        )
        save_ai_report("daily_review", f"{title}（AI生成失败）", source_text, failure_text)
        raise
    report_id = save_ai_report("daily_review", title, source_text, result)
    return report_id, result, context_text


def _build_technical_summaries(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for holding in holdings:
        result = get_daily_kline(holding["stock_code"], holding["market"], days=120)
        if not result.ok or result.data is None:
            summaries.append(
                {
                    "stock_name": holding["stock_name"],
                    "stock_code": holding["stock_code"],
                    "trend_summary": f"技术面数据获取失败：{result.error}",
                    "risk_notes": ["数据不足，不能判断K线风险。"],
                }
            )
            continue
        try:
            _, signals = analyze_kline(result.data)
            summaries.append(
                {
                    "stock_name": holding["stock_name"],
                    "stock_code": holding["stock_code"],
                    "current_price": signals["current_price"],
                    "trend_summary": signals["trend_summary"],
                    "risk_notes": signals["risk_notes"],
                }
            )
        except Exception as exc:
            summaries.append(
                {
                    "stock_name": holding["stock_name"],
                    "stock_code": holding["stock_code"],
                    "trend_summary": f"技术面分析失败：{exc}",
                    "risk_notes": ["技术数据不足，不能判断K线风险。"],
                }
            )
    return summaries
