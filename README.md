# Form Router

Сервис, который подбирает нужную форму обращения в IT Support по свободному описанию проблемы.
Пользователь пишет «не могу войти в учётку» или «в переговорке не работает проектор» — и сразу
получает ссылку на правильную форму, а не выбирает из десятка похожих. Тикет со страницы
не создаётся: сервис только маршрутизирует.

Зачем: меньше обращений «не в ту очередь», меньше ручных переназначений на первой линии.

**Как работает**

1. Упорядоченные правила (регулярные выражения) — мгновенно и предсказуемо.
2. Если правила не сработали — LLM через любой OpenAI-совместимый API (необязательно).
   Ответ модели валидируется: принимается только ключ формы из каталога.
3. Каталог форм (названия, ссылки, подсказки) — в JSON, без правки кода.

**Стек:** Python 3.11+, FastAPI, httpx, vanilla JS.

## Быстрый старт

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp forms.example.json forms.json   # подставьте ссылки на свои формы
cp .env.example .env               # по желанию: ключ LLM, CORS
.venv/bin/uvicorn form_router.app:app --port 8000
```

Откройте <http://127.0.0.1:8000/form-router/>.

Параметры страницы: `?q=текст` — предзаполнить, `?llm=0` — только правила,
`?api=https://host` — страница лежит отдельно (например, на вики), API — на другом хосте
(тогда задайте `FORM_ROUTER_CORS_ORIGIN`).

## API

| Метод | Путь | Описание |
| --- | --- | --- |
| `GET` | `/form-router/` | страница |
| `GET` | `/form-router/forms` | каталог форм |
| `POST` | `/form-router/classify` | `{"text": "...", "use_llm": true}` → `{"form", "why", "source"}` |

```bash
curl -s localhost:8000/form-router/classify -H 'Content-Type: application/json' \
  -d '{"text": "не печатает принтер"}'
# {"form":"diag","why":"оборудование / печать","source":"rules"}
```

Ключи форм: `account`, `corp`, `diag`, `software`, `internet`, `phone`, `meet`, `vks`, `move`, `other`.
Правила — в [`form_router/rules.py`](form_router/rules.py).

## Каталог форм

```json
{
  "title": "Какая форма нужна",
  "back": {"href": "https://wiki.example.com/it", "label": "Каталог IT Support"},
  "forms": {
    "account": {"label": "Учётная запись", "href": "https://...", "hint": "необязательная подсказка"},
    "other":   {"label": "Другая проблема", "href": "https://..."}
  }
}
```

Форма `other` обязательна; ссылки — только `http(s)`. Каталог проверяется при старте.

## Настройки

См. [`.env.example`](.env.example): `FORM_ROUTER_CATALOG`, `FORM_ROUTER_CORS_ORIGIN`,
`FORM_ROUTER_TRUST_PROXY`, `FORM_ROUTER_RATE_LIMIT`, `FORM_ROUTER_LLM`,
`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`.

## Безопасность

- Лимит запросов на IP (по умолчанию 30 в минуту). `X-Forwarded-For` учитывается
  только при `FORM_ROUTER_TRUST_PROXY=true` — иначе лимит легко обойти подменой заголовка.
- Текст ограничен 400 символами; ответ LLM принимается только как ключ из каталога.
- Страница собирает разметку через `textContent` — ответ сервера не попадает в HTML как код.
- CORS выключен, пока не задан `FORM_ROUTER_CORS_ORIGIN`.

## Тесты

```bash
.venv/bin/python -m pytest -q
```

## Лицензия

[MIT](LICENSE)
