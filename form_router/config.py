"""Настройки из окружения (или `.env` в корне репозитория)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _default_catalog() -> Path:
    own = REPO_ROOT / "forms.json"
    return own if own.is_file() else REPO_ROOT / "forms.example.json"


@dataclass(frozen=True)
class Settings:
    catalog_path: Path
    cors_origin: str
    trust_proxy: bool
    rate_limit_per_min: int
    llm_enabled: bool
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout_sec: float

    @property
    def llm_ready(self) -> bool:
        return self.llm_enabled and bool(self.llm_api_key and self.llm_model)


def load_settings() -> Settings:
    catalog = os.getenv("FORM_ROUTER_CATALOG", "").strip()
    return Settings(
        catalog_path=Path(catalog).expanduser() if catalog else _default_catalog(),
        cors_origin=os.getenv("FORM_ROUTER_CORS_ORIGIN", "").strip(),
        trust_proxy=_bool("FORM_ROUTER_TRUST_PROXY", False),
        rate_limit_per_min=max(1, int(os.getenv("FORM_ROUTER_RATE_LIMIT", "30"))),
        llm_enabled=_bool("FORM_ROUTER_LLM", True),
        llm_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        llm_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        llm_timeout_sec=float(os.getenv("FORM_ROUTER_LLM_TIMEOUT_SEC", "15")),
    )
