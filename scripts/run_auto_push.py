from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import init_db
from services.auto_push_service import run_auto_push


def main() -> None:
    parser = argparse.ArgumentParser(description="Run stock assistant automatic WeChat push once.")
    parser.add_argument("--force", action="store_true", help="Run once even if auto push is disabled.")
    args = parser.parse_args()

    init_db()
    result = run_auto_push(force=args.force)
    print(f"ok={result['ok']} pushed={result['pushed']} message={result['message']}")
    if result.get("report_id"):
        print(f"report_id={result['report_id']}")
    if result.get("report_error"):
        print(f"report_error={result['report_error']}")


if __name__ == "__main__":
    main()
