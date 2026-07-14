from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from config import settings
from services.indicator_service import analyze_kline
from services.market_data import get_daily_kline


RISK_LEVELS = ["正常", "注意", "风险预警", "严重风险"]

FINANCIAL_RISK_KEYWORDS = [
    "亏损",
    "净利润下降",
    "净利润下滑",
    "业绩下滑",
    "业绩下降",
    "营收下降",
    "现金流恶化",
    "负债率",
    "商誉减值",
    "监管问询",
    "立案调查",
    "退市风险",
    "ST",
    "减持",
    "质押",
    "债务逾期",
    "重大诉讼",
]


@dataclass
class RiskItem:
    stock_code: str
    stock_name: str
    category: str
    level: str
    reason: str
    evidence: str

    def as_dict(self) -> dict[str, str]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "category": self.category,
            "level": self.level,
            "reason": self.reason,
            "evidence": self.evidence,
        }


def scan_financial_text(text: str) -> dict[str, Any]:
    matched = []
    normalized = text or ""
    for keyword in FINANCIAL_RISK_KEYWORDS:
        if keyword.lower() in normalized.lower():
            matched.append(keyword)

    if any(k in matched for k in ["立案调查", "退市风险", "ST", "债务逾期", "重大诉讼"]):
        level = "严重风险"
    elif any(k in matched for k in ["亏损", "净利润下降", "净利润下滑", "业绩下滑", "业绩下降", "商誉减值"]):
        level = "风险预警"
    elif matched:
        level = "注意"
    else:
        level = "正常"

    return {
        "level": level,
        "matched_keywords": matched,
        "summary": "；".join(matched) if matched else "未命中明显暴雷关键词",
    }


def analyze_portfolio_risks(
    pnl_df: pd.DataFrame,
    total_assets: float | None = None,
    include_kline: bool = True,
) -> dict[str, Any]:
    items: list[RiskItem] = []
    warnings: list[str] = []

    if pnl_df.empty:
        return {
            "overall_level": "正常",
            "items": [],
            "industry_summary": [],
            "warnings": ["暂无持仓，无法计算风险。"],
        }

    position_base = total_assets if total_assets and total_assets > 0 else float(pnl_df["market_value"].dropna().sum())
    if not position_base:
        position_base = float(pnl_df["cost"].sum())

    _add_position_risks(items, pnl_df, position_base)
    industry_summary = _add_industry_risks(items, pnl_df, position_base)
    if total_assets and total_assets > 0:
        _add_total_position_risk(items, pnl_df, total_assets)
    else:
        warnings.append("未填写账户总资产，总股票仓位风险暂不判断。")

    if include_kline:
        _add_kline_risks(items, pnl_df, warnings)

    overall_level = highest_level([item.level for item in items])
    return {
        "overall_level": overall_level,
        "items": [item.as_dict() for item in items],
        "industry_summary": industry_summary,
        "warnings": warnings,
    }


def highest_level(levels: list[str]) -> str:
    if not levels:
        return "正常"
    return max(levels, key=lambda level: RISK_LEVELS.index(level))


def risk_items_to_markdown(risk_result: dict[str, Any]) -> str:
    lines = [f"## 今日风险等级：{risk_result['overall_level']}"]
    items = risk_result.get("items", [])
    if not items:
        lines.append("暂无明显暴雷、K线或仓位风险。")
    else:
        for item in items:
            lines.append(
                f"- [{item['level']}] {item['stock_name']}({item['stock_code']}) "
                f"{item['category']}：{item['reason']}。依据：{item['evidence']}"
            )
    warnings = risk_result.get("warnings") or []
    if warnings:
        lines.append("\n## 数据提示")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _add_position_risks(items: list[RiskItem], pnl_df: pd.DataFrame, position_base: float) -> None:
    if position_base <= 0:
        return
    for _, row in pnl_df.iterrows():
        value = row.get("market_value")
        if pd.isna(value):
            value = row.get("cost", 0)
        ratio = float(value) / position_base if position_base else 0
        if ratio > settings.RISK_SINGLE_POSITION_LIMIT:
            items.append(
                RiskItem(
                    stock_code=str(row["stock_code"]),
                    stock_name=str(row["stock_name"]),
                    category="仓位风险",
                    level="风险预警",
                    reason="单只股票仓位过高",
                    evidence=f"占比 {ratio * 100:.1f}%，超过 {settings.RISK_SINGLE_POSITION_LIMIT * 100:.0f}% 阈值",
                )
            )


def _add_total_position_risk(items: list[RiskItem], pnl_df: pd.DataFrame, total_assets: float) -> None:
    market_value = float(pnl_df["market_value"].dropna().sum())
    if market_value <= 0:
        market_value = float(pnl_df["cost"].sum())
    ratio = market_value / total_assets if total_assets else 0
    if ratio > settings.RISK_TOTAL_POSITION_LIMIT:
        items.append(
            RiskItem(
                stock_code="账户",
                stock_name="整体持仓",
                category="仓位风险",
                level="风险预警",
                reason="总股票仓位过高",
                evidence=f"总股票仓位 {ratio * 100:.1f}%，超过 {settings.RISK_TOTAL_POSITION_LIMIT * 100:.0f}% 阈值",
            )
        )


def _add_industry_risks(items: list[RiskItem], pnl_df: pd.DataFrame, position_base: float) -> list[dict[str, Any]]:
    if "industry" not in pnl_df.columns or position_base <= 0:
        return []

    df = pnl_df.copy()
    df["industry"] = df["industry"].fillna("").replace("", "未填写")
    df["risk_value"] = df["market_value"].fillna(df["cost"])
    grouped = df.groupby("industry", as_index=False)["risk_value"].sum()
    grouped["ratio"] = grouped["risk_value"] / position_base

    summary = []
    for _, row in grouped.sort_values("ratio", ascending=False).iterrows():
        industry = str(row["industry"])
        ratio = float(row["ratio"])
        summary.append({"industry": industry, "value": float(row["risk_value"]), "ratio": ratio})
        if industry != "未填写" and ratio > settings.RISK_INDUSTRY_LIMIT:
            items.append(
                RiskItem(
                    stock_code="行业",
                    stock_name=industry,
                    category="行业集中度",
                    level="注意",
                    reason="行业仓位集中",
                    evidence=f"{industry} 占比 {ratio * 100:.1f}%，超过 {settings.RISK_INDUSTRY_LIMIT * 100:.0f}% 阈值",
                )
            )
    return summary


def _add_kline_risks(items: list[RiskItem], pnl_df: pd.DataFrame, warnings: list[str]) -> None:
    for _, row in pnl_df.iterrows():
        stock_code = str(row["stock_code"])
        stock_name = str(row["stock_name"])
        market = str(row["market"])
        result = get_daily_kline(stock_code, market, days=90)
        if not result.ok or result.data is None:
            warnings.append(f"{stock_name}({stock_code}) K线风险无法判断：{result.error}")
            continue
        try:
            analyzed, signals = analyze_kline(result.data)
        except Exception as exc:
            warnings.append(f"{stock_name}({stock_code}) K线分析失败：{exc}")
            continue

        if signals.get("is_volume_down"):
            items.append(
                RiskItem(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    category="K线风险",
                    level="风险预警",
                    reason="放量下跌",
                    evidence=f"成交量约为5日均量 {signals.get('volume_ratio_vs_ma5', 0):.2f} 倍，且当日下跌",
                )
            )
        if signals.get("breaks_below_ma20"):
            items.append(
                RiskItem(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    category="K线风险",
                    level="风险预警",
                    reason="跌破 MA20",
                    evidence="前一交易日未跌破 MA20，最新收盘价跌破 MA20",
                )
            )
        if signals.get("breaks_below_ma60"):
            items.append(
                RiskItem(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    category="K线风险",
                    level="严重风险",
                    reason="跌破 MA60",
                    evidence="最新收盘价跌破中期均线 MA60",
                )
            )
        if _is_three_day_down(analyzed):
            items.append(
                RiskItem(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    category="K线风险",
                    level="注意",
                    reason="连续 3 天下跌",
                    evidence="最近 3 个交易日收盘价连续低于前一日",
                )
            )


def _is_three_day_down(df: pd.DataFrame) -> bool:
    if len(df) < 4:
        return False
    closes = df["close"].tail(4).tolist()
    return closes[1] < closes[0] and closes[2] < closes[1] and closes[3] < closes[2]

