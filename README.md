# EduMentor AI – Student Support Platform

A FastAPI-powered student support platform with PostgreSQL and Redis.

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL (async via asyncpg) |
| ORM | SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache / Queue | Redis + Celery |
| Auth | JWT (python-jose) + bcrypt |
| Validation | Pydantic v2 |
| Logging | Loguru |

## Quick Start

```bash
# 1. Clone & create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start the server
uvicorn main:app --reload --port 8000
```

API docs → http://localhost:8000/api/v1/docs

## Project Structure

```
EduMentor/
├── main.py                  # App entry point & CORS
├── requirements.txt
├── pyproject.toml           # Pytest + Ruff config
├── alembic.ini
├── .env.example
│
├── core/
│   ├── config.py            # Pydantic settings
│   ├── database.py          # Async SQLAlchemy engine
│   ├── redis.py             # Async Redis client
│   ├── security.py          # JWT + password hashing
│   └── logging.py           # Loguru setup
│
├── models/
│   ├── base.py              # UUIDMixin + TimestampMixin
│   ├── user.py              # User model
│   └── session.py           # Session model
│
├── schemas/
│   ├── user.py              # UserCreate/Update/Response + Token
│   ├── session.py           # SessionCreate/Update/Response
│   └── common.py            # PaginatedResponse, MessageResponse
│
├── services/
│   ├── user_service.py      # User DB operations
│   ├── session_service.py   # Session DB operations
│   └── cache_service.py     # Redis cache helpers
│
├── api/
│   ├── deps.py              # Auth dependencies & RBAC
│   └── v1/
│       ├── router.py        # Aggregate router
│       └── endpoints/
│           ├── auth.py      # POST /auth/register, /auth/login
│           ├── users.py     # GET/PATCH /users/me
│           └── sessions.py  # CRUD /sessions
│
├── alembic/
│   ├── env.py
│   └── script.py.mako
│
└── tests/
    ├── conftest.py          # In-memory SQLite fixtures
    └── test_auth.py
```

## Running Tests

```bash
pytest -v
```
