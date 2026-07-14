from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta
from typing import Callable

import pandas as pd

from services.portfolio_service import list_holdings


def fetch_digest_sources(max_items_per_stock: int = 5, timeout_seconds: int = 12) -> tuple[str, list[str]]:
    holdings = [holding for holding in list_holdings() if holding.get("market") == "A股"]
    if not holdings:
        return "", ["暂无 A股 持仓，无法自动抓取新闻公告。"]

    sections = []
    errors = []
    for holding in holdings:
        code = str(holding["stock_code"]).strip()
        name = str(holding["stock_name"]).strip()
        news_text, news_error = _run_with_timeout(
            lambda code=code: _fetch_stock_news(code, max_items_per_stock),
            timeout_seconds,
        )
        notice_text, notice_error = _run_with_timeout(
            lambda code=code: _fetch_stock_notices(code, max_items_per_stock),
            timeout_seconds,
        )

        stock_sections = []
        if news_text:
            stock_sections.append(f"【新闻】\n{news_text}")
        if notice_text:
            stock_sections.append(f"【公告】\n{notice_text}")
        if stock_sections:
            sections.append(f"## {name}({code})\n" + "\n\n".join(stock_sections))
        if news_error:
            errors.append(f"{name}({code}) 新闻抓取失败：{news_error}")
        if notice_error:
            errors.append(f"{name}({code}) 公告抓取失败：{notice_error}")

    return "\n\n".join(sections), errors


def _run_with_timeout(task: Callable[[], str], timeout_seconds: int) -> tuple[str, str]:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(task)
    try:
        return future.result(timeout=timeout_seconds), ""
    except TimeoutError:
        future.cancel()
        return "", f"超过 {timeout_seconds} 秒未返回"
    except Exception as exc:
        return "", str(exc)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _fetch_stock_news(stock_code: str, limit: int) -> str:
    import akshare as ak

    df = ak.stock_news_em(symbol=_clean_code(stock_code))
    return _format_dataframe_rows(df, limit)


def _fetch_stock_notices(stock_code: str, limit: int) -> str:
    import akshare as ak

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=14)).strftime("%Y%m%d")
    attempts = [
        lambda: ak.stock_zh_a_disclosure_report_cninfo(
            symbol=_clean_code(stock_code),
            market="沪深京",
            start_date=start_date,
            end_date=end_date,
        ),
        lambda: ak.stock_individual_notice_report(
            security=_clean_code(stock_code),
            symbol="全部",
            begin_date=start_date,
            end_date=end_date,
        ),
    ]
    last_error = ""
    for attempt in attempts:
        try:
            df = attempt()
            text = _format_dataframe_rows(df, limit)
            if text:
                return text
        except Exception as exc:
            last_error = str(exc)
    if last_error:
        raise RuntimeError(last_error)
    return ""


def _format_dataframe_rows(df: pd.DataFrame, limit: int) -> str:
    if df is None or df.empty:
        return ""
    rows = []
    for _, row in df.head(limit).iterrows():
        data = {str(key): "" if pd.isna(value) else str(value) for key, value in row.to_dict().items()}
        title = _first_value(data, ["标题", "title", "公告标题", "新闻标题", "name"])
        date = _first_value(data, ["日期", "时间", "公告日期", "date", "datetime", "发布时间"])
        source = _first_value(data, ["文章来源", "来源", "source"])
        url = _first_value(data, ["链接", "url", "公告链接"])
        content = _first_value(data, ["内容", "摘要", "summary", "新闻内容"])
        parts = [part for part in [date, title, source, content] if part]
        if not parts:
            parts = [f"{key}: {value}" for key, value in data.items() if value][:4]
        line = " | ".join(parts)
        if url:
            line = f"{line} | {url}"
        rows.append(f"- {line}")
    return "\n".join(rows)


def _first_value(data: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in data and data[key]:
            return data[key]
    return ""


def _clean_code(stock_code: str) -> str:
    return stock_code.lower().replace("sh", "").replace("sz", "").replace(".sh", "").replace(".sz", "").zfill(6)

