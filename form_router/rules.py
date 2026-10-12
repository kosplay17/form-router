"""Правила подбора формы. Порядок важен: более специфичные выше."""

from __future__ import annotations

import re
from dataclasses import dataclass

FORM_KEYS = (
    "account",
    "corp",
    "diag",
    "software",
    "internet",
    "phone",
    "meet",
    "vks",
    "move",
    "other",
)


@dataclass(frozen=True)
class Rule:
    form: str
    why: str
    pattern: re.Pattern[str]


def _rule(form: str, why: str, pattern: str) -> Rule:
    return Rule(form, why, re.compile(pattern, re.IGNORECASE))


RULES: tuple[Rule, ...] = (
    _rule("other", "выбрано «Другое»", r"^(?:другое|иное|нет\s+подходящ)"),
    _rule("meet", "переговорка / проектор", r"переговорк|проектор|подиум"),
    _rule("vks", "ВКС / Телемост", r"\bвкс\b|телемост|видеоконф|видеосвяз"),
    _rule("corp", "Telphin", r"телфин|telfin|telphin"),
    _rule(
        "phone",
        "телефония",
        r"софтфон|телефони|внутренн\w*\s+номер|"
        r"нет\s+(?:входящ|исходящ)|(?:входящ|исходящ)\w*\s+звонк",
    ),
    _rule("corp", "VPN", r"\bvpn\b|впн|anyconnect"),
    _rule(
        "account",
        "пароль / вход / учётная запись",
        r"парол|учетн|учётн|\b2fa\b|двухфактор|\bmfa\b|разблок|"
        r"не\s+(?:могу|получается)\s+(?:зайти|войти)|"
        r"active\s+directory|\bad\b|яндекс\s*360|yandex\s*360",
    ),
    _rule(
        "corp",
        "корпоративный сервис",
        r"пачк|pachca|pachka|\bwiki\b|вики|трекер|tracker|"
        r"почт|outlook|\b1\s*[cс]\b|"
        r"(?:писать|создавать|заводить)\s+задач|доступ\s+(?:к|в)\s+очеред|"
        r"нет\s+(?:доступа|возможност\w*).{0,80}(?:очеред|задач)",
    ),
    _rule(
        "software",
        "установка ПО",
        r"(?:нужно|хочу|помогите|прошу|требуется)\s+установ|"
        r"установ(?:ить|ка|ке|ки)\s+(?:по\b|программ|soft|office|приложен|клиент)|"
        r"инстал|поставить\s+программ|скачать\s+программ|"
        r"установ\w*\s+(?:на\s+)?(?:рабоч\w*\s+)?(?:ноут|пк|компьютер)|"
        r"acrobat|dbeaver|nanocad|нанокад",
    ),
    _rule(
        "move",
        "переезд / подключение оборудования",
        r"переезд|перемещ|перенести\s+(?:рабоч|компьютер|пк|монитор|оборудован)|"
        r"(?:подключить|отключить)\s+(?:новое\s+)?(?:рабоч\w*\s+мест|оборудован|монитор|док)",
    ),
    _rule(
        "diag",
        "оборудование / печать",
        r"принтер|мфу|печат|сканер|ноутбук|монитор|клавиатур|мыш[ьк]|"
        r"гарнитур|наушник|не\s+включается",
    ),
    _rule("internet", "интернет / Wi-Fi", r"интернет|wi-?fi|вай.?фай|нет\s+сети"),
)


def match_rule(text: str) -> Rule | None:
    for rule in RULES:
        if rule.pattern.search(text):
            return rule
    return None
