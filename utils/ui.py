from __future__ import annotations

from html import escape

import streamlit as st


def apply_app_style() -> None:
    """Apply one restrained, high-contrast visual system across all pages."""
    st.markdown(
        """
        <style>
        :root {
            --ink: #22272d;
            --ink-soft: #3f4a54;
            --muted: #697681;
            --line: #dce1e5;
            --line-strong: #c8d0d7;
            --paper: #ffffff;
            --canvas: #f5f7f8;
            --blue: #245f8f;
            --blue-dark: #19486d;
            --blue-soft: #edf4f8;
            --danger: #9e3430;
            --warning: #7b5619;
            --success: #27684f;
        }

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        }
        .stApp {
            background: var(--canvas);
            color: var(--ink);
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1260px;
            padding-top: 2.25rem;
            padding-bottom: 4.5rem;
        }
        [data-testid="stSidebar"] {
            background: var(--paper);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebarContent"] { padding-top: 1.1rem; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            border-left: 3px solid transparent;
            border-radius: 2px;
            min-height: 42px;
            padding: 8px 11px;
            color: var(--ink-soft) !important;
            font-weight: 520;
            transition: background-color .15s ease, border-color .15s ease;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: #f1f4f6;
            border-left-color: var(--line-strong);
            color: var(--ink) !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
            background: var(--blue-soft);
            border-left-color: var(--blue);
            color: var(--ink) !important;
            font-weight: 680;
        }
        .app-brand {
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 2px 2px 17px;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--line);
        }
        .app-brand-mark {
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            color: #ffffff;
            background: var(--blue);
            border-radius: 2px;
            font-size: 15px;
            font-weight: 760;
        }
        .app-brand-name {
            color: var(--ink);
            font-size: 16px;
            font-weight: 720;
            line-height: 1.3;
        }
        .app-brand-note {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.4;
        }

        .app-page-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 24px;
            padding: 3px 0 20px;
            border-bottom: 1px solid var(--line);
            margin-bottom: 26px;
        }
        .app-page-title-wrap { display: flex; align-items: center; gap: 14px; }
        .app-page-icon {
            width: 40px;
            height: 40px;
            display: grid;
            place-items: center;
            background: var(--paper);
            color: var(--blue-dark);
            border: 1px solid var(--line-strong);
            border-radius: 2px;
            font-size: 19px;
            flex: 0 0 40px;
        }
        .app-page-title {
            color: var(--ink);
            font-size: 26px;
            line-height: 1.25;
            font-weight: 720;
            letter-spacing: 0;
            margin: 0;
        }
        .app-page-subtitle {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.6;
            margin: 4px 0 0;
        }

        h1, h2, h3 {
            color: var(--ink) !important;
            letter-spacing: 0 !important;
        }
        h2 {
            font-size: 20px !important;
            font-weight: 700 !important;
            margin-top: 1.9rem !important;
            padding-bottom: .55rem;
            border-bottom: 1px solid var(--line);
        }
        h3 {
            font-size: 16px !important;
            font-weight: 680 !important;
            margin-top: 1.45rem !important;
        }
        p, li, label, [data-testid="stMarkdownContainer"],
        [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"] {
            color: var(--ink-soft);
            line-height: 1.65;
        }
        [data-testid="stCaptionContainer"] { color: var(--muted) !important; }

        [data-testid="stMetric"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-top: 3px solid var(--blue);
            border-radius: 2px;
            padding: 15px 17px 16px;
            min-height: 106px;
            box-shadow: none;
        }
        [data-testid="stMetricLabel"] * {
            color: var(--muted) !important;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] * {
            color: var(--ink) !important;
            font-size: 23px;
        }

        [data-testid="stForm"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 2px;
            padding: 22px;
        }
        [data-testid="stExpander"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 2px;
            overflow: hidden;
        }
        [data-testid="stExpander"] summary:hover { background: #f7f9fa; }
        [data-baseweb="tab-list"] {
            gap: 22px;
            background: transparent;
            padding: 0;
            border-bottom: 1px solid var(--line);
        }
        [data-baseweb="tab"] {
            border-radius: 0;
            min-height: 44px;
            padding: 0 2px;
            border-bottom: 3px solid transparent;
        }
        [data-baseweb="tab"] p { color: var(--muted) !important; font-weight: 600; }
        [aria-selected="true"][data-baseweb="tab"] {
            background: transparent;
            box-shadow: none;
            border-bottom-color: var(--blue);
        }
        [aria-selected="true"][data-baseweb="tab"] p { color: var(--ink) !important; }
        [data-baseweb="tab-highlight"] { display: none; }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 2px;
            min-height: 42px;
            font-weight: 650 !important;
            border: 1px solid var(--line-strong) !important;
            background: var(--paper) !important;
            color: var(--ink) !important;
            box-shadow: none !important;
            transition: background-color .15s ease, border-color .15s ease;
        }
        .stButton > button *, .stDownloadButton > button *,
        [data-testid="stFormSubmitButton"] > button * {
            color: inherit !important;
            font-weight: inherit !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            background: #f0f3f5 !important;
            border-color: #9da9b3 !important;
            color: var(--ink) !important;
        }
        button[kind^="primary"] {
            background: var(--blue) !important;
            border-color: var(--blue) !important;
            color: #ffffff !important;
        }
        button[kind^="primary"]:hover {
            background: var(--blue-dark) !important;
            border-color: var(--blue-dark) !important;
            color: #ffffff !important;
        }
        button:disabled, button:disabled * {
            background: #eef1f3 !important;
            border-color: var(--line) !important;
            color: #929ca5 !important;
        }

        input, textarea, [data-baseweb="select"] > div,
        [data-testid="stNumberInput"] button {
            background: var(--paper) !important;
            border-color: var(--line-strong) !important;
            color: var(--ink) !important;
            border-radius: 2px !important;
        }
        input, textarea, [data-baseweb="select"] * { color: var(--ink) !important; }
        input:focus, textarea:focus {
            border-color: var(--blue) !important;
            box-shadow: 0 0 0 1px var(--blue) !important;
        }
        [data-testid="stDataFrame"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 2px;
            overflow: hidden;
        }
        [data-testid="stAlert"] {
            border-radius: 2px;
            border-width: 1px;
            box-shadow: none;
        }
        [data-testid="stAlert"] * { color: var(--ink-soft) !important; }
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { color: inherit !important; }
        hr { border-color: var(--line) !important; }
        a { color: var(--blue-dark); }

        .data-freshness {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: var(--ink-soft);
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 2px;
            padding: 6px 10px;
            font-size: 13px;
            margin-bottom: 14px;
        }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--blue); }

        @media (max-width: 760px) {
            [data-testid="stMainBlockContainer"] { padding: 1.1rem 1rem 3rem; }
            .app-page-header { padding-bottom: 14px; margin-bottom: 16px; }
            .app-page-title { font-size: 22px; }
            .app-page-icon { width: 38px; height: 38px; flex-basis: 38px; }
            [data-testid="stMetric"] { min-height: 92px; padding: 12px; }
            [data-baseweb="tab-list"] { gap: 16px; overflow-x: auto; }
            [data-baseweb="tab"] { padding: 0 1px; font-size: 13px; white-space: nowrap; }
            [data-testid="stForm"] { padding: 16px; }
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
