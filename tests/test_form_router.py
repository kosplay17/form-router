from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from form_router import llm
from form_router.app import create_app
from form_router.catalog import CatalogError, validate_catalog
from form_router.config import REPO_ROOT, load_settings
from form_router.llm import parse_llm_answer
from form_router.service import classify_text

SETTINGS = replace(
    load_settings(),
    catalog_path=REPO_ROOT / "forms.example.json",
    llm_enabled=False,
    cors_origin="",
    trust_proxy=False,
    rate_limit_per_min=30,
)


@pytest.mark.parametrize(
    ("text", "form"),
    [
        ("не могу войти в учетку, забыл пароль", "account"),
        ("включить 2FA", "account"),
        ("не подключается VPN", "corp"),
        ("не могу войти в впн", "corp"),
        ("не работает почта", "corp"),
        ("нет доступа к очереди задач в трекере", "corp"),
        ("не работает 1С", "corp"),
        ("нет входящих звонков на внутренний номер", "phone"),
        ("Telphin не открывается", "corp"),
        ("нужно установить программу на ноутбук", "software"),
        ("установка dbeaver", "software"),
        ("не печатает принтер", "diag"),
        ("ноутбук не включается", "diag"),
        ("нет интернета, wifi пропал", "internet"),
        ("в переговорке не работает проектор", "meet"),
        ("организовать ВКС с партнёрами", "vks"),
        ("переезд на другой этаж", "move"),
        ("другое", "other"),
        ("", "other"),
    ],
)
def test_rules(text: str, form: str) -> None:
    assert classify_text(text, SETTINGS)["form"] == form


def test_unknown_text_without_llm_is_other() -> None:
    hit = classify_text("что-то странное происходит", SETTINGS)
    assert hit == {"form": "other", "why": "нет точного совпадения в правилах", "source": "rules"}


def test_llm_fallback_used_only_when_rules_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_complete(prompt: str, _settings) -> str:
        calls.append(prompt)
        return 'Ответ: {"form": "diag", "why": "похоже на железо"}'

    monkeypatch.setattr(llm, "_complete", fake_complete)
    on = replace(SETTINGS, llm_enabled=True, llm_api_key="test", llm_model="m")

    assert classify_text("не печатает принтер", on)["source"] == "rules"
    assert calls == []

    hit = classify_text("что-то странное происходит", on)
    assert hit == {"form": "diag", "why": "похоже на железо", "source": "llm"}
    assert "<text>что-то странное происходит</text>" in calls[0]

    assert classify_text("что-то странное", on, use_llm=False)["source"] == "rules"


@pytest.mark.parametrize(
    "content",
    ["", "нет json", '{"form": "hack"}', "[1, 2]", '{"form": 1'],
)
def test_parse_llm_answer_rejects_garbage(content: str) -> None:
    assert parse_llm_answer(content) is None


def test_parse_llm_answer_trims_why() -> None:
    hit = parse_llm_answer('{"form": "VKS", "why": "' + "x" * 500 + '"}')
    assert hit is not None and hit["form"] == "vks" and len(hit["why"]) == 120


def test_catalog_validation() -> None:
    good = {"forms": {"other": {"label": "Другое", "href": "https://example.com/o"}}}
    assert validate_catalog(good)["forms"]["other"]["hint"] == ""

    bad = [
        {},
        {"forms": {"account": {"label": "A", "href": "https://example.com/a"}}},
        {"forms": {"other": {"label": "O", "href": "javascript:alert(1)"}}},
        {"forms": {"other": {"label": "", "href": "https://example.com/o"}}},
        {"forms": {"other": {"label": "O", "href": "https://example.com/o"}, "nope": {}}},
    ]
    for data in bad:
        with pytest.raises(CatalogError):
            validate_catalog(data)


def test_api_page_forms_and_classify() -> None:
    client = TestClient(create_app(SETTINGS))
    assert client.get("/", follow_redirects=False).status_code == 307
    page = client.get("/form-router/")
    assert page.status_code == 200 and "Какая форма нужна" in page.text

    forms = client.get("/form-router/forms").json()
    assert set(forms["forms"]) >= {"account", "other"}

    res = client.post("/form-router/classify", json={"text": "сброс пароля"})
    assert res.status_code == 200
    assert res.json()["form"] == "account"
    assert "access-control-allow-origin" not in res.headers

    too_long = client.post("/form-router/classify", json={"text": "x" * 401})
    assert too_long.status_code == 422


def test_api_cors_when_configured() -> None:
    client = TestClient(create_app(replace(SETTINGS, cors_origin="https://wiki.example.com")))
    res = client.options("/form-router/classify")
    assert res.status_code == 204
    assert res.headers["access-control-allow-origin"] == "https://wiki.example.com"


def test_rate_limit_ignores_forwarded_for_by_default() -> None:
    client = TestClient(create_app(replace(SETTINGS, rate_limit_per_min=3)))
    codes = [
        client.post(
            "/form-router/classify",
            json={"text": "vpn"},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        ).status_code
        for i in range(4)
    ]
    assert codes == [200, 200, 200, 429]


def test_rate_limit_per_forwarded_ip_behind_trusted_proxy() -> None:
    client = TestClient(create_app(replace(SETTINGS, rate_limit_per_min=1, trust_proxy=True)))
    a = client.post("/form-router/classify", json={"text": "vpn"}, headers={"X-Forwarded-For": "1.1.1.1"})
    b = client.post("/form-router/classify", json={"text": "vpn"}, headers={"X-Forwarded-For": "2.2.2.2"})
    c = client.post("/form-router/classify", json={"text": "vpn"}, headers={"X-Forwarded-For": "1.1.1.1"})
    assert [a.status_code, b.status_code, c.status_code] == [200, 200, 429]
