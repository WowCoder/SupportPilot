"""
Unified LLM Client for SupportPilot.

Supports both OpenAI-compatible and Anthropic-compatible API formats,
configured via config/llm_config.yaml.
"""
import os
import logging
from typing import List, Dict, Optional

import requests
import yaml

logger = logging.getLogger(__name__)

# Absolute path to llm_config.yaml, resolved relative to this file
_LLM_CONFIG_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "llm_config.yaml"
)


class LLMClient:
    """Unified LLM client supporting OpenAI-compatible and Anthropic-compatible APIs."""

    def __init__(self, config_path: str = _LLM_CONFIG_DEFAULT):
        self._config_path = config_path
        self._config: Dict = {}
        self._provider: str = "openai_compatible"
        self._load_config()

    def _load_config(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("LLM config not found at %s, using defaults", self._config_path)
            self._config = {}
        self._provider = self._config.get("provider", "openai_compatible")

    def _get_api_key(self) -> Optional[str]:
        """Get API key with priority: yaml config -> flask config -> env var."""
        # 1. Config file api_key_env (env var name or literal key)
        provider_cfg = self._get_provider_config()
        key_env = provider_cfg.get("api_key_env", "")
        if key_env:
            env_val = os.environ.get(key_env)
            if env_val:
                return env_val
            if key_env.startswith("sk-"):
                return key_env

        # 2. Flask app config
        try:
            from flask import current_app
            val = current_app.config.get("LLM_API_KEY")
            if val:
                return val
        except RuntimeError:
            pass

        # 3. Environment variable
        return os.environ.get("LLM_API_KEY")

    def _get_provider_config(self) -> Dict:
        return self._config.get(self._provider, {})

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            messages: List of {"role": "system|user|assistant", "content": "..."}
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Generated text content, or error message string.
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.error("LLM_API_KEY is not configured")
            return "抱歉，API 密钥未配置，无法生成回复。"

        provider_cfg = self._get_provider_config()
        defaults = self._config.get("defaults", {})
        temp = temperature if temperature is not None else defaults.get("temperature", 0.7)
        tokens = max_tokens if max_tokens is not None else defaults.get("max_tokens", 1024)

        if self._provider == "anthropic_compatible":
            return self._call_anthropic(provider_cfg, api_key, messages, temp, tokens)
        else:
            return self._call_openai_compatible(provider_cfg, api_key, messages, temp, tokens)

    def chat(
        self,
        query: str,
        context: Optional[str | List] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Convenience method: generate a response from a user query with optional context.

        Args:
            query: User query string
            context: Optional context (str, list of str, or list of dict with content/similarity)
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            Generated text content, or error message string.
        """
        if system_prompt is None:
            system_prompt = "你是一个 helpful 的客户支持助手。使用提供的知识来回答用户问题。如果知识库中没有相关信息，请诚实地告诉用户。"

        context_str = self._format_context(context)
        user_content = f"{context_str}\n\n用户问题：{query}" if context_str else query

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return self.generate(messages, temperature, max_tokens)

    @staticmethod
    def _format_context(context: Optional[str | List]) -> str:
        """Format context into a string for prompt building."""
        if not context:
            return ""
        if isinstance(context, str):
            return f"相关知识：{context}"
        if isinstance(context, list) and context:
            if isinstance(context[0], dict):
                return "\n".join(
                    f"相关知识：{item['content']} (相似度：{item['similarity']:.2f})"
                    for item in context
                    if item.get("similarity", 0) > 0.1
                )
            return "\n".join(f"相关知识：{item}" for item in context)
        return ""

    def _call_openai_compatible(
        self, cfg: Dict, api_key: str, messages: List[Dict], temperature: float, max_tokens: int
    ) -> str:
        """Call an OpenAI-compatible chat completions endpoint."""
        api_base = cfg.get("api_base", "").rstrip("/")
        model = cfg.get("model", "deepseek-v4-flash")
        timeout = cfg.get("timeout", 30)
        url = f"{api_base}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            logger.warning("Unexpected API response format: %s", data)
            return "抱歉，无法解析 AI 回复，请稍后重试。"
        except requests.exceptions.Timeout:
            logger.error("LLM request timeout")
            return "抱歉，AI 服务响应超时，请稍后重试。"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            logger.error("LLM HTTP error %s: %s", status, e)
            if status == 401:
                return "抱歉，API 密钥验证失败。"
            elif status == 429:
                return "抱歉，API 请求过于频繁，请稍后重试。"
            return f"抱歉，AI 服务返回错误（状态码：{status}）。"
        except requests.exceptions.ConnectionError:
            logger.error("LLM connection error")
            return "抱歉，无法连接到 AI 服务，请检查网络连接。"
        except Exception:
            logger.error("LLM request failed", exc_info=True)
            return "抱歉，AI 服务请求失败，请稍后重试。"

    def _call_anthropic(
        self, cfg: Dict, api_key: str, messages: List[Dict], temperature: float, max_tokens: int
    ) -> str:
        """Call an Anthropic-compatible Messages endpoint."""
        api_base = cfg.get("api_base", "").rstrip("/")
        model = cfg.get("model", "claude-sonnet-4-6")
        timeout = cfg.get("timeout", 30)
        anthropic_version = cfg.get("anthropic_version", "2023-06-01")
        url = f"{api_base}/messages"

        # Extract system message from messages list
        system_content = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
        }
        if system_content:
            payload["system"] = system_content

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": anthropic_version,
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if "content" in data and len(data["content"]) > 0:
                return data["content"][0]["text"]
            logger.warning("Unexpected API response format: %s", data)
            return "抱歉，无法解析 AI 回复，请稍后重试。"
        except requests.exceptions.Timeout:
            logger.error("LLM request timeout")
            return "抱歉，AI 服务响应超时，请稍后重试。"
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            logger.error("LLM HTTP error %s: %s", status, e)
            if status == 401:
                return "抱歉，API 密钥验证失败。"
            elif status == 429:
                return "抱歉，API 请求过于频繁，请稍后重试。"
            return f"抱歉，AI 服务返回错误（状态码：{status}）。"
        except requests.exceptions.ConnectionError:
            logger.error("LLM connection error")
            return "抱歉，无法连接到 AI 服务，请检查网络连接。"
        except Exception:
            logger.error("LLM request failed", exc_info=True)
            return "抱歉，AI 服务请求失败，请稍后重试。"


# Global singleton
llm_client = LLMClient()
