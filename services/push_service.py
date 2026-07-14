from __future__ import annotations

import requests

from config import settings
from services.settings_service import get_bool_setting, get_setting


class PushError(Exception):
    """Raised when a push provider request fails."""


def get_push_config() -> dict[str, str | bool]:
    return {
        "provider": get_setting("push_provider", ""),
        "token": get_setting("push_token", ""),
        "enabled": get_bool_setting("push_enabled", False),
    }


def send_wechat_push(title: str, content: str) -> str:
    config = get_push_config()
    provider = str(config["provider"])
    token = str(config["token"])
    enabled = bool(config["enabled"])

    if not enabled:
        raise PushError("微信推送未启用，请先在系统设置中启用。")
    if provider not in {"Server酱", "PushPlus"}:
        raise PushError("请选择 Server酱 或 PushPlus 推送类型。")
    if not token:
        raise PushError("请先填写 SendKey 或 PushPlus Token。")

    if provider == "Server酱":
        return _send_server_chan(token, title, content)
    return _send_pushplus(token, title, content)


def _send_server_chan(send_key: str, title: str, content: str) -> str:
    try:
        response = requests.post(
            f"https://sctapi.ftqq.com/{send_key}.send",
            data={"title": title, "desp": content},
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = _safe_json(response)
        code = payload.get("code")
        if code not in {0, 200, "0", "200", None}:
            raise PushError(f"Server酱返回失败：{payload}")
        return f"Server酱推送请求已发送。返回：{payload or response.text[:120]}"
    except requests.RequestException as exc:
        raise PushError(f"Server酱推送失败：{exc}") from exc


def _send_pushplus(token: str, title: str, content: str) -> str:
    try:
        response = requests.post(
            "https://www.pushplus.plus/send",
            json={"token": token, "title": title, "content": content, "template": "markdown"},
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = _safe_json(response)
        code = payload.get("code")
        if code not in {200, "200"}:
            msg = payload.get("msg") or payload.get("message") or response.text[:300]
            raise PushError(f"PushPlus 返回失败：code={code}，msg={msg}")
        return f"PushPlus 推送成功：{payload.get('msg') or '请求已受理'}"
    except requests.RequestException as exc:
        raise PushError(f"PushPlus 推送失败：{exc}") from exc


def _safe_json(response: requests.Response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}
