"""Классификация текста: сначала правила, при промахе — LLM."""

from __future__ import annotations

import re

from form_router.config import Settings
from form_router.llm import classify_with_llm
from form_router.rules import match_rule

MAX_TEXT = 400


def classify_text(text: str, settings: Settings, *, use_llm: bool = True) -> dict:
    raw = re.sub(r"\s+", " ", (text or "").strip())[:MAX_TEXT]
    if not raw:
        return {"form": "other", "why": "пустой текст", "source": "rules"}

    rule = match_rule(raw)
    if rule:
        return {"form": rule.form, "why": rule.why, "source": "rules"}

    if use_llm:
        llm_hit = classify_with_llm(raw, settings)
        if llm_hit:
            return llm_hit

    return {"form": "other", "why": "нет точного совпадения в правилах", "source": "rules"}
