from __future__ import annotations

from urllib.parse import quote

from services.settings_service import get_setting, set_setting


def get_public_app_url() -> str:
    return get_setting("public_app_url", "")


def save_public_app_url(url: str) -> None:
    set_setting("public_app_url", url.strip())


def build_qr_code_url(url: str, size: int = 240) -> str:
    encoded = quote(url.strip(), safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded}"

