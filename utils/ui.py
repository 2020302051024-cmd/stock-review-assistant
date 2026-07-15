from __future__ import annotations

from html import escape

import streamlit as st


def apply_app_style() -> None:
    """Apply one restrained visual system across all Streamlit pages."""
    st.markdown(
        """
        <style>
        :root {
            --ink: #202a35;
            --muted: #687582;
            --line: #dfe4e8;
            --panel: #ffffff;
            --canvas: #f7f8fa;
            --accent: #245f8f;
            --accent-dark: #174a72;
            --accent-soft: #eaf2f8;
            --gain: #d13f37;
            --loss: #15906b;
        }

        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stMainBlockContainer"] {
            max-width: 1320px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebarNavLink"] {
            border-radius: 3px;
            margin: 2px 8px;
            min-height: 42px;
        }
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: var(--accent-soft);
            color: var(--accent-dark);
            font-weight: 650;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            border-radius: 3px;
            min-height: 40px;
            padding: 7px 10px;
            color: #344054;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: #edf3f7;
            color: var(--accent-dark);
        }

        .app-page-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            padding: 2px 0 18px;
            border-bottom: 1px solid var(--line);
            margin-bottom: 22px;
        }
        .app-page-title-wrap { display: flex; align-items: center; gap: 13px; }
        .app-page-icon {
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            background: var(--accent-soft);
            color: var(--accent-dark);
            border: 1px solid #cfdeea;
            border-radius: 3px;
            font-size: 21px;
            flex: 0 0 42px;
        }
        .app-page-title {
            color: var(--ink);
            font-size: 27px;
            line-height: 1.25;
            font-weight: 750;
            letter-spacing: 0;
            margin: 0;
        }
        .app-page-subtitle {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.6;
            margin: 4px 0 0;
        }

        h1, h2, h3 { color: var(--ink); letter-spacing: 0 !important; }
        h2 { font-size: 21px !important; margin-top: 1.8rem !important; }
        h3 { font-size: 17px !important; margin-top: 1.35rem !important; }
        p, label, [data-testid="stCaptionContainer"] { line-height: 1.6; }

        [data-testid="stMetric"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 3px;
            padding: 15px 17px;
            min-height: 104px;
            box-shadow: none;
        }
        [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
        [data-testid="stMetricValue"] { color: var(--ink); font-size: 24px; }

        [data-testid="stForm"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 3px;
            padding: 20px;
        }
        [data-testid="stExpander"] {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 3px;
            overflow: hidden;
        }
        [data-baseweb="tab-list"] {
            gap: 4px;
            background: #edf1f4;
            padding: 4px;
            border-radius: 3px;
        }
        [data-baseweb="tab"] {
            border-radius: 2px;
            min-height: 40px;
            padding: 0 16px;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            background: #ffffff;
            color: var(--accent-dark);
            box-shadow: none;
            border: 1px solid #cfdeea;
        }
        [data-baseweb="tab-highlight"] { display: none; }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 3px;
            min-height: 40px;
            font-weight: 650;
            border-color: #b9c5cf;
            background: #ffffff;
            color: #28465e;
        }
        button[kind="primary"] {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
        }
        button[kind="primary"]:hover {
            background: var(--accent-dark) !important;
            border-color: var(--accent-dark) !important;
        }
        [data-testid="stDataFrame"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 3px;
            overflow: hidden;
        }
        [data-testid="stAlert"] { border-radius: 3px; }
        hr { border-color: var(--line) !important; }

        .data-freshness {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: #475467;
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 3px;
            padding: 6px 10px;
            font-size: 13px;
            margin-bottom: 14px;
        }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); }

        @media (max-width: 760px) {
            [data-testid="stMainBlockContainer"] { padding: 1.1rem 1rem 3rem; }
            .app-page-header { padding-bottom: 14px; margin-bottom: 16px; }
            .app-page-title { font-size: 22px; }
            .app-page-icon { width: 38px; height: 38px; flex-basis: 38px; }
            [data-testid="stMetric"] { min-height: 92px; padding: 12px; }
            [data-baseweb="tab"] { padding: 0 11px; font-size: 13px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="app-page-header">
          <div class="app-page-title-wrap">
            <div class="app-page-icon">{escape(icon)}</div>
            <div>
              <h1 class="app-page-title">{escape(title)}</h1>
              <p class="app-page-subtitle">{escape(subtitle)}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_data_freshness(updated_at: str, label: str = "数据更新时间") -> None:
    st.markdown(
        f'<div class="data-freshness"><span class="status-dot"></span>{escape(label)}：{escape(str(updated_at))}</div>',
        unsafe_allow_html=True,
    )
