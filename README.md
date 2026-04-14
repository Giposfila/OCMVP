# VerifyAI — MVP

Аналитический ИИ-ассистент для верификации информации.

## Стек

- Backend: FastAPI + PostgreSQL + SQLAlchemy (async)
- Frontend: Jinja2 + Vanilla JS
- Auth: Cookie-сессии

## Быстрый старт

### Через Docker:

```bash
docker compose up --build
```

Открыть: http://localhost:8000

### Локально:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Открыть: http://localhost:8000

## Тестовые аккаунты

- elena@test.ru / test123 (StandardUser)
- artem@test.ru / test123 (ProfessionalAnalyst)
- admin@test.ru / admin123 (Admin)

## Реализованные экраны

1. Landing (/) — ввод текста для проверки
2. Loading (/claims/{id}/loading) — мультиагентный процессинг
3. Report (/claims/{id}/report) — аналитический отчёт с Индексом
4. History (/history) — реестр проверок пользователя

## Структура API

- `GET /` — Landing страница
- `POST /claims/submit` — создание запроса
- `GET /claims/{id}/loading` — страница загрузки
- `GET /claims/{id}/report` — отчёт
- `GET /history` — история
- `GET /api/claims/{id}/status` — статус API
- `GET /api/claims` — список запросов
- `DELETE /api/claims/{id}` — удаление
- `GET /auth/login`, `POST /auth/login` — вход
- `GET /auth/register`, `POST /auth/register` — регистрация
- `POST /auth/logout` — выход