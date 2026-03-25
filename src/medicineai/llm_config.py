"""Shared LangChain ChatOpenAI configuration."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def build_chat_model() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs = {"model": model, "api_key": api_key, "temperature": 0.2}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)
