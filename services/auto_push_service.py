from __future__ import annotations

from datetime import datetime
from typing import Any

from services.cache_service import set_json_cache
from services.daily_review_service import generate_and_save_daily_review
from services.dashboard_service import build_dashboard_snapshot
from services.push_service import PushError, send_wechat_push
from services.risk_service import risk_items_to_markdown
from services.settings_service import get_bool_setting, get_setting, set_setting
from utils.formatters import format_money, format_percent


AUTO_PUSH_CACHE_KEY = "auto_push_last_result"


def get_auto_push_config() -> dict[str, Any]:
    return {
        "enabled": get_bool_setting("auto_push_enabled", False),
        "push_time": get_setting("auto_push_time", "09:00"),
        "include_kline": get_bool_setting("auto_push_include_kline", True),
        "fetch_market_price": get_bool_setting("auto_push_fetch_market_price", True),
        "generate_daily_review": get_bool_setting("auto_push_generate_daily_review", False),
        "total_assets": _safe_float(get_setting("auto_push_total_assets", "0")),
    }


def save_auto_push_config(
    enabled: bool,
    push_time: str,
    include_kline: bool,
    fetch_market_price: bool,
    generate_daily_review: bool,
    total_assets: float,
) -> None:
    set_setting("auto_push_enabled", "true" if enabled else "false")
    set_setting("auto_push_time", _normalize_time(push_time))
    set_setting("auto_push_include_kline", "true" if include_kline else "false")
    set_setting("auto_push_fetch_market_price", "true" if fetch_market_price else "false")
    set_setting("auto_push_generate_daily_review", "true" if generate_daily_review else "false")
    set_setting("auto_push_total_assets", str(max(0.0, float(total_assets or 0))))


def run_auto_push(
    force: bool = False,
    manual_prices: dict[int, float] | None = None,
) -> dict[str, Any]:
    config = get_auto_push_config()
    if not config["enabled"] and not force:
        result = {
            "ok": False,
            "pushed": False,
            "message": "自动推送未启用。可在系统设置中启用，或使用脚本 --force 强制执行一次。",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        set_json_cache(AUTO_PUSH_CACHE_KEY, result)
        return result

    snapshot = build_dashboard_snapshot(
        manual_prices=manual_prices or {},
        fetch_market_price=bool(config["fetch_market_price"]),
        include_kline=bool(config["include_kline"]),
        total_assets=config["total_assets"] if config["total_assets"] > 0 else None,
    )
    title = "股票复盘助手：自动风险摘要"
    content = build_auto_push_markdown(snapshot, config)

    report_id = None
    report_error = ""
    if config["generate_daily_review"]:
        try:
            report_id, _, _ = generate_and_save_daily_review(
                notes="自动推送任务生成",
                fetch_market_price=bool(config["fetch_market_price"]),
                include_technical=bool(config["include_kline"]),
                title="自动推送每日复盘",
            )
        except Exception as exc:
            report_error = str(exc)
            content += f"\n\n## 复盘生成提示\n- 自动复盘生成失败：{report_error}"

    try:
        push_message = send_wechat_push(title, content)
        result = {
            "ok": True,
            "pushed": True,
            "message": push_message,
            "report_id": report_id,
            "report_error": report_error,
            "snapshot": snapshot,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    except PushError as exc:
        result = {
            "ok": False,
            "pushed": False,
            "message": str(exc),
            "report_id": report_id,
            "report_error": report_error,
            "snapshot": snapshot,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    set_json_cache(AUTO_PUSH_CACHE_KEY, result)
    return result


def build_auto_push_markdown(snapshot: dict[str, Any], config: dict[str, Any]) -> str:
    summary = snapshot.get("summary", {})
    risk_result = snapshot.get("risk_result", {})
    lines = [
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 账户概览",
        f"- 今日风险等级：{risk_result.get('overall_level', '正常')}",
        f"- 总浮动盈亏：{format_money(summary.get('total_floating_pnl'))}",
        f"- 总收益率：{format_percent(summary.get('total_return_rate'))}",
        f"- 风险条目数：{len(risk_result.get('items', []))}",
        "",
        risk_items_to_markdown(risk_result),
    ]
    warnings = summary.get("errors") or []
    if warnings:
        lines.append("\n## 行情提示")
        lines.extend(f"- {warning}" for warning in warnings)
    lines.append("\n提示：本推送只做复盘和风险提醒，不构成买入或卖出建议。")
    if not config.get("include_kline"):
        lines.append("本次未检查 K线风险。")
    return "\n".join(lines)


def _normalize_time(value: str) -> str:
    text = (value or "09:00").strip()
    parts = text.split(":")
    if len(parts) != 2:
        return "09:00"
    try:
        hour = max(0, min(23, int(parts[0])))
        minute = max(0, min(59, int(parts[1])))
    except ValueError:
        return "09:00"
    return f"{hour:02d}:{minute:02d}"


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
