from __future__ import annotations

from prompts.financial_report_prompt import FINANCIAL_REPORT_SYSTEM_PROMPT, build_daily_market_digest_prompt
from services.deepseek_service import DeepSeekClient
from services.portfolio_service import list_holdings
from services.report_service import save_ai_report
from services.risk_service import scan_financial_text
from services.settings_service import get_setting, set_setting


def get_focus_areas() -> str:
    return get_setting("market_digest_focus_areas", "")


def save_focus_areas(value: str) -> None:
    set_setting("market_digest_focus_areas", value)


def build_portfolio_digest_context() -> str:
    holdings = list_holdings()
    if not holdings:
        return "暂无持仓。"

    lines = []
    for holding in holdings:
        lines.append(
            "- "
            f"{holding.get('stock_name')}({holding.get('stock_code')}): "
            f"行业 {holding.get('industry') or '未填写'}, "
            f"投资逻辑 {holding.get('investment_logic') or '未填写'}, "
            f"重点监控 {'是' if holding.get('is_watchlist') else '否'}, "
            f"备注 {holding.get('note') or '无'}"
        )
    return "\n".join(lines)


def generate_market_digest(source_text: str, focus_areas: str | None = None) -> tuple[int, str, str]:
    focus = focus_areas if focus_areas is not None else get_focus_areas()
    portfolio_context = build_portfolio_digest_context()
    risk_scan = scan_financial_text(source_text)
    prompt = build_daily_market_digest_prompt(portfolio_context, focus, source_text)
    client = DeepSeekClient()
    result = client.generate_text(
        prompt,
        system_prompt=FINANCIAL_REPORT_SYSTEM_PROMPT,
        temperature=0.15,
    )
    saved_result = (
        f"关键词风险等级：{risk_scan['level']}\n"
        f"命中关键词：{risk_scan['summary']}\n\n"
        f"{result}"
    )
    source = (
        f"持仓上下文：\n{portfolio_context}\n\n"
        f"关注领域：\n{focus}\n\n"
        f"当天材料：\n{source_text}"
    )
    report_id = save_ai_report("market_digest", "每日消息面汇总报告", source, saved_result)
    return report_id, saved_result, source

