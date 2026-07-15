HOLDINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    market TEXT NOT NULL,
    buy_price REAL NOT NULL CHECK (buy_price >= 0),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    buy_date TEXT NOT NULL,
    industry TEXT DEFAULT '',
    investment_logic TEXT DEFAULT '',
    is_watchlist INTEGER NOT NULL DEFAULT 0,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
);
"""


REPORTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ai_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    report_type TEXT NOT NULL,
    title TEXT NOT NULL,
    source_text TEXT DEFAULT '',
    ai_result TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
);
"""


USER_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, key),
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
);
"""


MARKET_SNAPSHOTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    market TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    price REAL,
    data_json TEXT DEFAULT '',
    source TEXT DEFAULT '',
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (stock_code, market, snapshot_type)
);
"""


TRADE_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    holding_id INTEGER,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    action TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    reason TEXT DEFAULT '',
    emotion TEXT DEFAULT '',
    discipline_note TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE,
    FOREIGN KEY (holding_id) REFERENCES holdings(id) ON DELETE SET NULL
);
"""


APP_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


APP_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


APP_USERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS app_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


ALL_TABLES_SQL = [
    HOLDINGS_TABLE_SQL,
    REPORTS_TABLE_SQL,
    APP_SETTINGS_TABLE_SQL,
    APP_CACHE_TABLE_SQL,
    APP_USERS_TABLE_SQL,
    USER_SETTINGS_TABLE_SQL,
    MARKET_SNAPSHOTS_TABLE_SQL,
    TRADE_LOGS_TABLE_SQL,
]
