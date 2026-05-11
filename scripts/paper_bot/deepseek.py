"""Thin DeepSeek client (OpenAI-compatible API)."""
from __future__ import annotations

import json
import os

from openai import OpenAI

_DEFAULT_BASE = "https://api.deepseek.com"


def _model() -> str:
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.environ.get("DEEPSEEK_BASE_URL", _DEFAULT_BASE),
    )


def chat(
    messages: list[dict],
    *,
    json_mode: bool = False,
    max_tokens: int = 1500,
    temperature: float = 0.2,
) -> str:
    kwargs: dict = {
        "model": _model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat_json(messages: list[dict], *, max_tokens: int = 2000) -> dict:
    return json.loads(chat(messages, json_mode=True, max_tokens=max_tokens))
