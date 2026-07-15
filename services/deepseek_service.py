from __future__ import annotations

import json
import time
from typing import Any

try:
    import requests
    from requests import exceptions as requests_exceptions
except ImportError:
    requests = None
    requests_exceptions = None

from config import settings
from services.deepseek_config_service import get_deepseek_config


class DeepSeekError(Exception):
    """Raised when DeepSeek API calls fail in a user-displayable way."""


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        saved_config = get_deepseek_config()
        self.api_key = api_key or saved_config["api_key"]
        self.base_url = (base_url or saved_config["base_url"]).rstrip("/")
        self.model = model or saved_config["model"]
        self.thinking = saved_config["thinking"]
        self.reasoning_effort = saved_config["reasoning_effort"]
        self.timeout = timeout or _safe_int(saved_config.get("timeout_seconds"), 90)
        self.max_retries = _safe_int(saved_config.get("max_retries"), 1)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_text(
        self,
        prompt: str,
        system_prompt: str = "你是一个严谨、通俗的中文助手。",
        temperature: float = 0.2,
    ) -> str:
        data = self._chat_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format=None,
        )
        return self._extract_content(data)

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "你是一个只输出 JSON 的助手。",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        data = self._chat_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = self._extract_content(data)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise DeepSeekError(f"模型返回的 JSON 无法解析：{exc}") from exc

    def _chat_completion(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        response_format: dict[str, str] | None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise DeepSeekError("未配置 DeepSeek API Key，请先在“系统设置”页面填写。")
        if requests is None:
            raise DeepSeekError("缺少 requests 依赖，请先执行 pip install -r requirements.txt。")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        elif self.model == "deepseek-v4-pro":
            payload["thinking"] = {"type": self.thinking}
            payload["reasoning_effort"] = self.reasoning_effort

        last_error: Exception | None = None
        attempts = max(1, self.max_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except requests.Timeout as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(min(2 * attempt, 5))
                    continue
                raise DeepSeekError(
                    f"DeepSeek API 响应超时：已等待 {self.timeout} 秒并重试 {self.max_retries} 次。"
                    "通常是模型繁忙、网络波动或输入内容过长。可以稍后重试、减少分析内容，"
                    "或在系统设置里把模型临时改为 deepseek-chat / 调高超时时间。"
                ) from exc
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "未知"
                message = exc.response.text[:300] if exc.response is not None else str(exc)
                if status in {429, 500, 502, 503, 504} and attempt < attempts:
                    last_error = exc
                    time.sleep(min(2 * attempt, 5))
                    continue
                raise DeepSeekError(f"DeepSeek API 返回错误，状态码 {status}：{message}") from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < attempts and _is_retryable_request_error(exc):
                    time.sleep(min(2 * attempt, 5))
                    continue
                raise DeepSeekError(f"DeepSeek API 请求失败：{exc}") from exc
            except ValueError as exc:
                raise DeepSeekError("DeepSeek API 返回内容不是合法 JSON。") from exc

        raise DeepSeekError(f"DeepSeek API 请求失败：{last_error}")

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError("DeepSeek API 返回结构异常，未找到模型文本内容。") from exc


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_retryable_request_error(exc: Exception) -> bool:
    if requests_exceptions is None:
        return False
    return isinstance(
        exc,
        (
            requests_exceptions.ConnectionError,
            requests_exceptions.ChunkedEncodingError,
        ),
    )
