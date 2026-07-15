import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from database.models import ALL_TABLES_SQL


def ensure_data_dir() -> None:
    """Create the database parent directory when it does not exist."""
    Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with dict-like row access enabled."""
    ensure_data_dir()
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    """Provide a managed database connection and close it reliably."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize all MVP database tables."""
    with db_connection() as conn:
        for statement in ALL_TABLES_SQL:
            conn.execute(statement)
        migrate_db(conn)


def migrate_db(conn: sqlite3.Connection) -> None:
    """Apply lightweight additive migrations for existing local databases."""
    holding_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(holdings)").fetchall()
    }
    migrations = {
        "user_id": "ALTER TABLE holdings ADD COLUMN user_id INTEGER",
        "industry": "ALTER TABLE holdings ADD COLUMN industry TEXT DEFAULT ''",
        "investment_logic": "ALTER TABLE holdings ADD COLUMN investment_logic TEXT DEFAULT ''",
        "is_watchlist": "ALTER TABLE holdings ADD COLUMN is_watchlist INTEGER NOT NULL DEFAULT 0",
    }
    for column, statement in migrations.items():
        if column not in holding_columns:
            conn.execute(statement)

    report_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ai_reports)").fetchall()
    }
    if "user_id" not in report_columns:
        conn.execute("ALTER TABLE ai_reports ADD COLUMN user_id INTEGER")

    owner = conn.execute(
        "SELECT id FROM app_users WHERE is_active = 1 ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if not owner:
        return

    owner_id = int(owner["id"])
    conn.execute("UPDATE holdings SET user_id = ? WHERE user_id IS NULL", (owner_id,))
    conn.execute("UPDATE ai_reports SET user_id = ? WHERE user_id IS NULL", (owner_id,))
    conn.execute(
        """
        INSERT OR IGNORE INTO user_settings (user_id, key, value, updated_at)
        SELECT ?, key, value, updated_at FROM app_settings
        """,
        (owner_id,),
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON holdings(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_id ON ai_reports(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_logs_user_id ON trade_logs(user_id)")


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {settings.DATABASE_PATH}")
