"""Каталог форм: куда вести пользователя для каждого ключа. Хранится в JSON."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from form_router.rules import FORM_KEYS


class CatalogError(ValueError):
    pass


def _check_url(value: object, where: str) -> str:
    url = str(value or "").strip()
    if urlparse(url).scheme not in {"http", "https"}:
        raise CatalogError(f"{where}: нужен http(s) URL, получено {url!r}")
    return url


def load_catalog(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"не удалось прочитать каталог {path}: {exc}") from exc
    return validate_catalog(data)


def validate_catalog(data: object) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("forms"), dict):
        raise CatalogError("в каталоге нет объекта forms")

    forms: dict[str, dict] = {}
    for key, item in data["forms"].items():
        if key not in FORM_KEYS:
            raise CatalogError(f"неизвестный ключ формы {key!r}; допустимы: {', '.join(FORM_KEYS)}")
        if not isinstance(item, dict) or not str(item.get("label") or "").strip():
            raise CatalogError(f"forms.{key}: нужен label")
        forms[key] = {
            "label": str(item["label"]).strip(),
            "href": _check_url(item.get("href"), f"forms.{key}.href"),
            "hint": str(item.get("hint") or "").strip(),
        }
    if "other" not in forms:
        raise CatalogError("в каталоге обязательна форма other")

    back = data.get("back")
    return {
        "title": str(data.get("title") or "Какая форма нужна").strip(),
        "back": (
            {"href": _check_url(back.get("href"), "back.href"), "label": str(back.get("label") or "Назад")}
            if isinstance(back, dict) and back.get("href")
            else None
        ),
        "forms": forms,
    }
