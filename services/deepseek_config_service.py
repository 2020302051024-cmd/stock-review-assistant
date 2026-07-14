from __future__ import annotations

from config import settings
from services.settings_service import get_setting, set_setting


def get_deepseek_config() -> dict[str, str]:
    return {
        "api_key": get_setting("deepseek_api_key", settings.DEEPSEEK_API_KEY),
        "base_url": get_setting("deepseek_base_url", settings.DEEPSEEK_BASE_URL),
        "model": get_setting("deepseek_model", settings.DEEPSEEK_MODEL),
        "thinking": get_setting("deepseek_thinking", settings.DEEPSEEK_THINKING),
        "reasoning_effort": get_setting("deepseek_reasoning_effort", settings.DEEPSEEK_REASONING_EFFORT),
    }


def save_deepseek_config(
    api_key: str,
    base_url: str,
    model: str,
    thinking: str,
    reasoning_effort: str,
) -> None:
    set_setting("deepseek_api_key", api_key.strip())
    set_setting("deepseek_base_url", base_url.strip().rstrip("/") or "https://api.deepseek.com")
    set_setting("deepseek_model", model.strip() or "deepseek-v4-pro")
    set_setting("deepseek_thinking", thinking.strip() or "enabled")
    set_setting("deepseek_reasoning_effort", reasoning_effort.strip() or "high")

