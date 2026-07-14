from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import init_db
from services.daily_review_service import generate_and_save_daily_review


def main() -> None:
    init_db()
    report_id, _, _ = generate_and_save_daily_review(
        notes="自动定时生成",
        fetch_market_price=True,
        include_technical=True,
        title="每日自动复盘报告",
    )
    print(f"Daily review generated. report_id={report_id}")


if __name__ == "__main__":
    main()

