"""LLM 客户端抽象层 — 支持 OpenAI / Anthropic / Moonshot(Kimi) 三个提供商。

Moonshot (Kimi) 使用 OpenAI 兼容 API，通过 openai SDK + 自定义 base_url 访问。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

# 提供商常量
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_MOONSHOT = "moonshot"

# 默认模型
DEFAULT_MODELS = {
    PROVIDER_OPENAI: "gpt-4o-mini",
    PROVIDER_ANTHROPIC: "claude-sonnet-4-20250514",
    PROVIDER_MOONSHOT: "moonshot-v1-8k",
}

# 环境变量
ENV_KEYS = {
    PROVIDER_OPENAI: "OPENAI_API_KEY",
    PROVIDER_ANTHROPIC: "ANTHROPIC_API_KEY",
    PROVIDER_MOONSHOT: "MOONSHOT_API_KEY",
}

MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"


@dataclass
class LLMConfig:
    """LLM 客户端配置。"""

    provider: str = PROVIDER_MOONSHOT
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    api_key: str | None = None
    base_url: str | None = None

    def __post_init__(self):
        if self.provider not in DEFAULT_MODELS:
            raise ValueError(
                f"不支持的提供商: {self.provider}，"
                f"支持: {', '.join(DEFAULT_MODELS.keys())}"
            )
        if self.model is None:
            self.model = DEFAULT_MODELS[self.provider]
        if self.api_key is None:
            env_var = ENV_KEYS[self.provider]
            self.api_key = os.environ.get(env_var)
        if self.provider == PROVIDER_MOONSHOT and self.base_url is None:
            self.base_url = MOONSHOT_BASE_URL


@dataclass
class LLMUsage:
    """Token 用量追踪。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """统一的 LLM 返回结果。"""

    content: str = ""
    usage: LLMUsage = field(default_factory=LLMUsage)
    success: bool = True
    error: str | None = None


class LLMClient:
    """统一 LLM 客户端，延迟初始化 SDK。"""

    def __init__(self, config: LLMConfig | None = None, **kwargs: Any):
        if config is None:
            config = LLMConfig(**kwargs)
        self.config = config
        self._client: Any = None

    def _ensure_client(self):
        """延迟初始化底层 SDK 客户端。"""
        if self._client is not None:
            return

        if not self.config.api_key:
            env_var = ENV_KEYS[self.config.provider]
            raise ValueError(
                f"缺少 API key，请设置环境变量 {env_var} "
                f"或通过 api_key 参数传入"
            )

        if self.config.provider in (PROVIDER_OPENAI, PROVIDER_MOONSHOT):
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "需要安装 openai 包: pip install 'knowlyr-datalabel[openai]'"
                )
            kwargs: dict[str, Any] = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = OpenAI(**kwargs)

        elif self.config.provider == PROVIDER_ANTHROPIC:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "需要安装 anthropic 包: pip install 'knowlyr-datalabel[anthropic]'"
                )
            self._client = Anthropic(api_key=self.config.api_key)

    def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        """发送聊天请求。

        Args:
            messages: 消息列表，格式: [{"role": "system"|"user"|"assistant", "content": "..."}]

        Returns:
            LLMResponse 统一返回
        """
        try:
            self._ensure_client()
        except (ValueError, ImportError) as e:
            return LLMResponse(success=False, error=str(e))

        try:
            if self.config.provider in (PROVIDER_OPENAI, PROVIDER_MOONSHOT):
                return self._chat_openai(messages)
            else:
                return self._chat_anthropic(messages)
        except Exception as e:
            return LLMResponse(success=False, error=str(e))

    def _chat_openai(self, messages: list[dict[str, str]]) -> LLMResponse:
        """OpenAI / Moonshot 兼容 API 调用。"""
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        usage = LLMUsage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
        )
        content = resp.choices[0].message.content or ""
        return LLMResponse(content=content, usage=usage)

    def _chat_anthropic(self, messages: list[dict[str, str]]) -> LLMResponse:
        """Anthropic API 调用 — system 消息需分离。"""
        system_text = ""
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                api_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": api_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        if system_text.strip():
            kwargs["system"] = system_text.strip()

        resp = self._client.messages.create(**kwargs)
        usage = LLMUsage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        content = resp.content[0].text if resp.content else ""
        return LLMResponse(content=content, usage=usage)

    def chat_json(self, messages: list[dict[str, str]]) -> tuple[Any, LLMResponse]:
        """发送聊天请求并解析 JSON 返回。

        自动去除 markdown 代码围栏后解析 JSON。

        Returns:
            (parsed_json, LLMResponse) 元组
        """
        response = self.chat(messages)
        if not response.success:
            return None, response

        text = response.content.strip()
        # 去除 markdown 代码围栏: ```json ... ``` 或 ``` ... ```
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        try:
            parsed = json.loads(text)
            return parsed, response
        except json.JSONDecodeError as e:
            return None, LLMResponse(
                content=response.content,
                usage=response.usage,
                success=False,
                error=f"JSON 解析失败: {e}",
            )
