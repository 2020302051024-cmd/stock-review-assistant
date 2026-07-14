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
    pnl_df, summary = calculate_portfolio_pnl(
        holdings,
        manual_prices=manual_prices or {},
        fetch_market_price=fetch_market_price,
    )
    risk_result = analyze_portfolio_risks(
        pnl_df,
        total_assets=total_assets if total_assets and total_assets > 0 else None,
        include_kline=include_kline,
    )
    return {
        "summary": summary,
        "risk_result": risk_result,
        "pnl_rows": pnl_df.to_dict(orient="records"),
    }

