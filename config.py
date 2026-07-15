from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")
else:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Settings:
    """Application settings loaded from environment variables."""

    APP_NAME = "股票复盘助手"
    DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/stock_assistant.db")

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    DEEPSEEK_THINKING = os.getenv("DEEPSEEK_THINKING", "enabled")
    DEEPSEEK_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")

    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    MARKET_TIMEOUT_SECONDS = int(os.getenv("MARKET_TIMEOUT_SECONDS", "8"))

    RISK_SINGLE_POSITION_LIMIT = float(os.getenv("RISK_SINGLE_POSITION_LIMIT", "0.30"))
    RISK_TOTAL_POSITION_LIMIT = float(os.getenv("RISK_TOTAL_POSITION_LIMIT", "0.70"))
    RISK_INDUSTRY_LIMIT = float(os.getenv("RISK_INDUSTRY_LIMIT", "0.40"))


settings = Settings()
