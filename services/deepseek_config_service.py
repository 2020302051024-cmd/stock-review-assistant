from __future__ import annotations

from config import settings
from services.settings_service import get_setting, set_setting
from services.user_context import primary_user_id, resolve_user_id


def get_deepseek_config() -> dict[str, str]:
    owner_id = resolve_user_id()
    use_env_defaults = owner_id == primary_user_id()
    return {
        "api_key": get_setting("deepseek_api_key", settings.DEEPSEEK_API_KEY if use_env_defaults else ""),
        "base_url": get_setting("deepseek_base_url", settings.DEEPSEEK_BASE_URL),
        "model": get_setting("deepseek_model", settings.DEEPSEEK_MODEL),
        "thinking": get_setting("deepseek_thinking", settings.DEEPSEEK_THINKING),
        "reasoning_effort": get_setting("deepseek_reasoning_effort", settings.DEEPSEEK_REASONING_EFFORT),
        "timeout_seconds": get_setting("deepseek_timeout_seconds", "90"),
        "max_retries": get_setting("deepseek_max_retries", "1"),
    }


def save_deepseek_config(
    api_key: str,
    base_url: str,
    model: str,
    thinking: str,
    reasoning_effort: str,
    timeout_seconds: int | str = 90,
    max_retries: int | str = 1,
) -> None:
    set_setting("deepseek_api_key", api_key.strip())
    set_setting("deepseek_base_url", base_url.strip().rstrip("/") or "https://api.deepseek.com")
    set_setting("deepseek_model", model.strip() or "deepseek-v4-pro")
    set_setting("deepseek_thinking", thinking.strip() or "enabled")
    set_setting("deepseek_reasoning_effort", reasoning_effort.strip() or "high")
    set_setting("deepseek_timeout_seconds", str(_clamp_int(timeout_seconds, default=90, minimum=15, maximum=180)))
    set_setting("deepseek_max_retries", str(_clamp_int(max_retries, default=1, minimum=0, maximum=3)))


def _clamp_int(value: int | str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))
