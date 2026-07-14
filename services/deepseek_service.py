from __future__ import annotations

import json
from typing import Any

try:
    import requests
except ImportError:
    requests = None

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
        self.timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS

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
            raise DeepSeekError("DeepSeek API 请求超时，请稍后重试或调大 REQUEST_TIMEOUT_SECONDS。") from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "未知"
            message = exc.response.text[:300] if exc.response is not None else str(exc)
            raise DeepSeekError(f"DeepSeek API 返回错误，状态码 {status}：{message}") from exc
        except requests.RequestException as exc:
            raise DeepSeekError(f"DeepSeek API 请求失败：{exc}") from exc
        except ValueError as exc:
            raise DeepSeekError("DeepSeek API 返回内容不是合法 JSON。") from exc

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError("DeepSeek API 返回结构异常，未找到模型文本内容。") from exc
