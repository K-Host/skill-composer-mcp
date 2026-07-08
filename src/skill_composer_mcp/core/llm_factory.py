"""
LLM 工厂 - 多LLM提供商支持（Ollama / OpenAI / Anthropic）
默认使用 Ollama 本地模型，无需 API Key
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from loguru import logger


class LLMProvider(Protocol):
    """LLM 提供商接口"""

    async def chat(self, prompt: str, system: str = "") -> str:
        ...


class OllamaProvider:
    """Ollama 本地模型提供商（默认，无需 API Key）"""

    def __init__(self, model: str = "qwen2.5:7b", base_url: str | None = None):
        self._model = model
        self._base_url = base_url or "http://localhost:11434"
        self._client = None

    async def chat(self, prompt: str, system: str = "") -> str:
        try:
            import ollama

            self._client = ollama.Client(host=self._base_url)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self._client.chat(model=self._model, messages=messages)
            return response["message"]["content"]
        except ImportError:
            logger.warning("ollama 包未安装，使用 HTTP API")
            return await self._chat_via_http(prompt, system)
        except Exception as e:
            logger.error(f"Ollama 调用失败: {e}")
            return f"[Ollama 错误: {e}]"

    async def _chat_via_http(self, prompt: str, system: str) -> str:
        """通过 HTTP API 调用 Ollama"""
        import aiohttp

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/api/chat",
                json={"model": self._model, "messages": messages, "stream": False},
            ) as resp:
                data = await resp.json()
                return data.get("message", {}).get("content", "")


class OpenAIProvider:
    """OpenAI 提供商"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    async def chat(self, prompt: str, system: str = "") -> str:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = await client.chat.completions.create(
                model=self._model, messages=messages
            )
            return response.choices[0].message.content or ""
        except ImportError:
            logger.error("openai 包未安装")
            return "[错误: openai 包未安装]"
        except Exception as e:
            logger.error(f"OpenAI 调用失败: {e}")
            return f"[OpenAI 错误: {e}]"


class AnthropicProvider:
    """Anthropic 提供商"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key
        self._model = model

    async def chat(self, prompt: str, system: str = "") -> str:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self._api_key)
            response = await client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system or None,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except ImportError:
            logger.error("anthropic 包未安装")
            return "[错误: anthropic 包未安装]"
        except Exception as e:
            logger.error(f"Anthropic 调用失败: {e}")
            return f"[Anthropic 错误: {e}]"


class RuleBasedProvider:
    """规则引擎（默认回退，不依赖外部 LLM）"""

    async def chat(self, prompt: str, system: str = "") -> str:
        """基于规则的简单推荐"""
        # 这个方法在 recommend_combo 中被特殊处理
        # 这里只提供一个占位实现
        return json.dumps(
            {
                "note": "使用规则引擎，未调用 LLM",
                "prompt_received": prompt[:200],
            },
            ensure_ascii=False,
        )


class LLMFactory:
    """LLM 工厂"""

    @staticmethod
    def create(
        provider: str = "ollama",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> LLMProvider:
        """创建 LLM 提供商实例"""
        provider_lower = provider.lower()

        if provider_lower == "ollama":
            return OllamaProvider(
                model=model or "qwen2.5:7b", base_url=base_url
            )
        elif provider_lower == "openai":
            if not api_key:
                logger.warning("OpenAI 未提供 API Key，回退到规则引擎")
                return RuleBasedProvider()
            return OpenAIProvider(
                api_key=api_key, model=model or "gpt-4o-mini", base_url=base_url
            )
        elif provider_lower == "anthropic":
            if not api_key:
                logger.warning("Anthropic 未提供 API Key，回退到规则引擎")
                return RuleBasedProvider()
            return AnthropicProvider(api_key=api_key, model=model or "claude-sonnet-4-20250514")
        else:
            logger.warning(f"未知 LLM 提供商: {provider}，回退到规则引擎")
            return RuleBasedProvider()
