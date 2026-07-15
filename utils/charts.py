from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


UP_COLOR = "#ef4444"
DOWN_COLOR = "#16a34a"
MA_COLORS = {
    "ma5": "#d69b2d",
    "ma10": "#2b6f9f",
    "ma20": "#5e86a3",
    "ma60": "#7d8790",
}


def build_kline_figure(df: pd.DataFrame, ma_windows: list[int]) -> go.Figure:
    """Build a stock-app-like candlestick chart with volume, MACD and RSI."""
    chart_df = df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"])
    volume_colors = [
        UP_COLOR if close >= open_ else DOWN_COLOR
        for open_, close in zip(chart_df["open"], chart_df["close"])
    ]
    macd_colors = [UP_COLOR if value >= 0 else DOWN_COLOR for value in chart_df["macd"].fillna(0)]

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[0.56, 0.18, 0.16, 0.10],
        subplot_titles=("K线与均线", "成交量", "MACD", "RSI"),
    )

    fig.add_trace(
        go.Candlestick(
            x=chart_df["date"],
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="K线",
            increasing_line_color=UP_COLOR,
            increasing_fillcolor=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            decreasing_fillcolor=DOWN_COLOR,
        ),
        row=1,
        col=1,
    )

    for window in ma_windows:
        column = f"ma{window}"
        if column in chart_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=chart_df["date"],
                    y=chart_df[column],
                    mode="lines",
                    name=f"MA{window}",
                    line={"width": 1.4, "color": MA_COLORS.get(column, "#475569")},
                ),
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Bar(
            x=chart_df["date"],
            y=chart_df["volume"],
            name="成交量",
            marker_color=volume_colors,
            opacity=0.72,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=chart_df["date"],
            y=chart_df["macd"],
            name="MACD柱",
            marker_color=macd_colors,
            opacity=0.72,
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["dif"],
            mode="lines",
            name="DIF",
            line={"width": 1.3, "color": "#2b6f9f"},
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["dea"],
            mode="lines",
            name="DEA",
            line={"width": 1.3, "color": "#f59e0b"},
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=chart_df["date"],
            y=chart_df["rsi"],
            mode="lines",
            name="RSI",
            line={"width": 1.5, "color": "#245f8f"},
        ),
        row=4,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dot", line_color="#94a3b8", row=4, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#94a3b8", row=4, col=1)

    fig.update_layout(
        height=820,
        margin={"l": 24, "r": 24, "t": 48, "b": 24},
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        xaxis_rangeslider_visible=False,
        template="plotly_white",
    )
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="#94a3b8",
        spikethickness=1,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", fixedrange=False)
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="量", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=4, col=1)
    return fig
