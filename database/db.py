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
        "industry": "ALTER TABLE holdings ADD COLUMN industry TEXT DEFAULT ''",
        "investment_logic": "ALTER TABLE holdings ADD COLUMN investment_logic TEXT DEFAULT ''",
        "is_watchlist": "ALTER TABLE holdings ADD COLUMN is_watchlist INTEGER NOT NULL DEFAULT 0",
    }
    for column, statement in migrations.items():
        if column not in holding_columns:
            conn.execute(statement)


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {settings.DATABASE_PATH}")
