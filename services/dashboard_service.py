from __future__ import annotations

from typing import Any

from services.portfolio_service import list_holdings
from services.report_service import calculate_portfolio_pnl
from services.risk_service import analyze_portfolio_risks


def build_dashboard_snapshot(
    manual_prices: dict[int, float] | None = None,
    fetch_market_price: bool = True,
    include_kline: bool = True,
    total_assets: float | None = None,
) -> dict[str, Any]:
    holdings = list_holdings()
    market_results = {}
    pnl_df, summary = calculate_portfolio_pnl(
        holdings,
        manual_prices=manual_prices or {},
        fetch_market_price=fetch_market_price,
        market_results=market_results,
        market_days=90 if include_kline else 5,
    )
    risk_result = analyze_portfolio_risks(
        pnl_df,
        total_assets=total_assets if total_assets and total_assets > 0 else None,
        include_kline=include_kline,
        market_results=market_results,
    )
    pnl_rows = pnl_df.to_dict(orient="records")
    valid_prices = sum(1 for row in pnl_rows if row.get("current_price") is not None)
    cached_prices = sum(
        1 for row in pnl_rows if str(row.get("price_source", "")).startswith("缓存")
    )
    return {
        "summary": summary,
        "risk_result": risk_result,
        "pnl_rows": pnl_rows,
        "data_status": {
            "total": len(pnl_rows),
            "valid_prices": valid_prices,
            "cached_prices": cached_prices,
            "live_prices": max(0, valid_prices - cached_prices),
        },
    }
