from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = """Ты — аналитик. Ниже представлен документ с обезличенными данными.
Плейсхолдеры вида <PERSON_1>, <ORG_1>, <INN_1> и т.д. заменяют реальные значения.

Задача: проанализируй документ и предоставь результат.

Отвечай на русском языке. Сохраняй плейсхолдеры как есть — НЕ заменяй их на реальные данные."""


@dataclass
class AIConfig:
    service: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""
    prompt: str = DEFAULT_PROMPT
    temperature: float = 0.3
    max_tokens: int = 4096


class AIService(ABC):
    @abstractmethod
    def send(self, prompt: str, text: str, config: AIConfig) -> str:
        ...

    @abstractmethod
    def test_connection(self, config: AIConfig) -> bool:
        ...


class OpenAIClient(AIService):
    def send(self, prompt: str, text: str, config: AIConfig) -> str:
        import openai

        client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url or None,
        )

        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def test_connection(self, config: AIConfig) -> bool:
        try:
            import openai

            client = openai.OpenAI(
                api_key=config.api_key,
                base_url=config.base_url or None,
            )
            client.models.list()
            return True
        except Exception:
            return False


class AnthropicClient(AIService):
    def send(self, prompt: str, text: str, config: AIConfig) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=config.api_key)

        response = client.messages.create(
            model=config.model,
            max_tokens=config.max_tokens,
            system=prompt,
            messages=[{"role": "user", "content": text}],
        )
        return response.content[0].text

    def test_connection(self, config: AIConfig) -> bool:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=config.api_key)
            client.messages.create(
                model=config.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


class OllamaClient(AIService):
    def send(self, prompt: str, text: str, config: AIConfig) -> str:
        import requests

        base_url = config.base_url or "http://localhost:11434"
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def test_connection(self, config: AIConfig) -> bool:
        try:
            import requests

            base_url = config.base_url or "http://localhost:11434"
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class CustomClient(AIService):
    def send(self, prompt: str, text: str, config: AIConfig) -> str:
        import openai

        client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def test_connection(self, config: AIConfig) -> bool:
        try:
            import openai

            client = openai.OpenAI(
                api_key=config.api_key,
                base_url=config.base_url,
            )
            client.models.list()
            return True
        except Exception:
            return False


_SERVICES: dict[str, AIService] = {
    "openai": OpenAIClient(),
    "anthropic": AnthropicClient(),
    "ollama": OllamaClient(),
    "custom": CustomClient(),
}


def get_ai_client(service: str) -> AIService:
    if service not in _SERVICES:
        raise ValueError(f"Неизвестный AI-сервис: {service}. Доступные: {list(_SERVICES.keys())}")
    return _SERVICES[service]


def send_to_ai(text: str, config: AIConfig) -> str:
    client = get_ai_client(config.service)
    return client.send(config.prompt, text, config)


def test_ai_connection(config: AIConfig) -> bool:
    client = get_ai_client(config.service)
    return client.test_connection(config)
