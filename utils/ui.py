from __future__ import annotations

from html import escape

import streamlit as st


def apply_app_style(page_tone: str = "neutral") -> None:
    """Apply the shared warm-neutral visual system across all pages."""
    st.markdown(
        """
        <style>
        :root {
            --ink: #3d3a35;
            --ink-soft: #5b5650;
            --muted: #7d766d;
            --line: #e1dbd1;
            --line-strong: #cec4b6;
            --paper: #fffdf8;
            --canvas: #f4f1ea;
            --wood: #88715b;
            --wood-dark: #6f5c4a;
            --wood-soft: #eee7dc;
            --action: var(--wood);
            --action-dark: var(--wood-dark);
            --action-soft: var(--wood-soft);
            --danger: #9a4e48;
            --danger-dark: #7f3f3a;
            --danger-soft: #f3e5e1;
            --warning: #826733;
            --success: #58745e;
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
            animation: quiet-enter .28s ease-out both;
        }
        @keyframes quiet-enter {
            from { opacity: 0; transform: translateY(3px); }
            to { opacity: 1; transform: translateY(0); }
        }
        [data-testid="stSidebar"] {
            background: #faf7f0;
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
            background: #f1ece3;
            border-left-color: var(--line-strong);
            color: var(--ink) !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
            background: var(--action-soft);
            border-left-color: var(--action);
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
            background: var(--action);
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
            color: var(--action-dark);
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
            border-top: 2px solid var(--action);
            border-radius: 4px;
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
            border-radius: 4px;
            padding: 22px;
        }
        [data-testid="stExpander"] {
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 4px;
            overflow: hidden;
        }
        [data-testid="stExpander"] summary:hover { background: #f7f3ec; }
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
            border-bottom-color: var(--action);
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
            background: #f1ede5 !important;
            border-color: #b8ad9e !important;
            color: var(--ink) !important;
        }
        button[kind^="primary"] {
            background: var(--action) !important;
            border-color: var(--action) !important;
            color: #ffffff !important;
        }
        button[kind^="primary"]:hover {
            background: var(--action-dark) !important;
            border-color: var(--action-dark) !important;
            color: #ffffff !important;
        }
        button:disabled, button:disabled * {
            background: #ece8e0 !important;
            border-color: var(--line) !important;
            color: #9a9389 !important;
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
            border-color: var(--action) !important;
            box-shadow: 0 0 0 1px var(--action) !important;
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
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {
            background: #eeebe4 !important;
            border: 1px solid #ddd6cb !important;
        }
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {
            background: #f3eddd !important;
            border: 1px solid #dfd1ab !important;
        }
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {
            background: var(--danger-soft) !important;
            border: 1px solid #ddc2bd !important;
        }
        [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
            background: #e8eee7 !important;
            border: 1px solid #cad7c8 !important;
        }
        hr { border-color: var(--line) !important; }
        a { color: var(--action-dark); }

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
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--action); }

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
        @media (prefers-reduced-motion: reduce) {
            [data-testid="stMainBlockContainer"] { animation: none; }
            * { transition-duration: 0.01ms !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if page_tone == "danger":
        st.markdown(
            """
            <style>
            .stApp {
                --action: var(--danger);
                --action-dark: var(--danger-dark);
                --action-soft: var(--danger-soft);
            }
            .app-page-header--danger { border-bottom-color: #ddc2bd; }
            .app-page-header--danger .app-page-icon {
                color: var(--danger-dark);
                background: var(--danger-soft);
                border-color: #ddc2bd;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def render_page_header(title: str, subtitle: str, icon: str, tone: str = "neutral") -> None:
    tone_class = " app-page-header--danger" if tone == "danger" else ""
    st.markdown(
        f"""
        <div class="app-page-header{tone_class}">
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
