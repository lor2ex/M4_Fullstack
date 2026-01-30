## Рефакторинг проекта: от "ручного" управления БД до FastAPI

### Шаг 0. Структура проекта

```
project/
├── docker-compose.yml
├── .env
├── people.json
└── app/
    ├── __init__.py
    ├── main.py
    ├── db/
    │   ├── __init__.py
    │   ├── initial_data.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── person.py     # ORM Person + Pydantic схемы
    │   └── repository/
    │       ├── __init__.py
    │       └── person.py
    └── routers/
        └── people.py

```

Добавить недостающие пакеты:

```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg python-dotenv pydantic[email]
```

` pydantic[email]` понадобится для валидации поля почты

---

### Шаг 1. Docker + .env

**docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:17
    container_name: async_postgres
    env_file:
      - .env
    ports:
      - "5435:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**.env**

```
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydb
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
```

---

### Шаг 2. DB конфигурация (`app/db/__init__.py`)

```python
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
```

---

### Шаг 3. Модель Person (`app/db/models/person.py`)

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from pydantic import BaseModel, EmailStr
from app.db import Base

# ---------- ORM ----------
class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, unique=True)


# ---------- Pydantic схемы ----------
class PersonCreate(BaseModel):
    name: str
    age: int | None = None
    email: EmailStr

class PersonRead(BaseModel):
    id: int
    name: str
    age: int | None = None
    email: EmailStr

    model_config = {
        "from_attributes": True  # SQLAlchemy -> Pydantic v2
    }

```

**`app/db/models/__init__.py`**

```python
from .person import Person, PersonCreate, PersonRead
# Позже: from .book import Book, BookCreate, BookRead
```

---

### Шаг 4. Репозиторий Person (`app/db/repository/person.py`)

```python
from sqlalchemy import select, func
from app.db import AsyncSessionLocal
from app.db.models.person import Person

class PersonRepository:

    @staticmethod
    async def is_table_empty() -> bool:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(select(func.count()).select_from(Person))
            return count == 0

    @staticmethod
    async def list_people() -> list[Person]:
        async with AsyncSessionLocal() as session:
            result = await session.scalars(select(Person))
            return result.all()

    @staticmethod
    async def create_person(name: str, age: int | None, email: str) -> Person:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = Person(name=name, age=age, email=email)
                session.add(person)
            return person

    @staticmethod
    async def update_email(person_id: int, new_email: str) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = await session.get(Person, person_id)
                if not person:
                    return False
                person.email = new_email
                return True

    @staticmethod
    async def delete_person(person_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                person = await session.get(Person, person_id)
                if not person:
                    return False
                await session.delete(person)
                return True
```

**`app/db/repository/__init__.py`**

```python
from .person import PersonRepository
# Позже: from .book import BookRepository
```

---

### Шаг 5. Инициализация базы + загрузка данных (`app/db/initial_data.py`)

```python
import json
from app.db import engine
from app.db.models import Person
from app.db.repository import PersonRepository
from app.db import Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def load_people_from_json(json_file: str):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        await PersonRepository.create_person(
            name=item["name"],
            age=item.get("age"),
            email=item.get("email")
        )
```

---

### Шаг 6. Pydantic v2 модели и маршруты (`app/routers/people.py`)

```python
from fastapi import APIRouter, HTTPException
from typing import List
from app.db.models.person import PersonCreate, PersonRead
from app.db.repository import PersonRepository

router = APIRouter(prefix="/people", tags=["people"])

@router.get("/", response_model=List[PersonRead])
async def read_people():
    return await PersonRepository.list_people()

@router.post("/", response_model=PersonRead)
async def add_person(person: PersonCreate):
    return await PersonRepository.create_person(person.name, person.age, person.email)

@router.put("/{person_id}/email")
async def update_email(person_id: int, new_email: str):
    updated = await PersonRepository.update_email(person_id, new_email)
    if not updated:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Email updated successfully"}

@router.delete("/{person_id}")
async def delete_person(person_id: int):
    deleted = await PersonRepository.delete_person(person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person deleted successfully"}

```

---

### Шаг 7. Основной файл FastAPI (`app/main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db.initial_data import (
    init_db,
    load_people_from_json,
    load_books_from_json,
)
from app.db.repository import PersonRepository, BookRepository
from app.routers import people, books


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----------------------
    #        STARTUP
    # ----------------------
    await init_db()

    # --- Загрузка людей ---
    if await PersonRepository.is_table_empty():
        await load_people_from_json("people.json")

    # --- Загрузка книг ---
    if await BookRepository.is_tables_empty():
        await load_books_from_json("books.json")

    yield

    # ----------------------
    #       SHUTDOWN
    # ----------------------
    # Здесь можно освободить ресурсы


app = FastAPI(
    title="People + Books API v2",
    lifespan=lifespan,
)

# Роутеры
app.include_router(people.router)
app.include_router(books.router)
```

---

### Пояснения

1. Структура готова к будущему **расширению на книги**:

   * Для `Book` достаточно создать `app/db/models/book.py` и `app/db/repository/book.py`.
   * И импортировать их в `__init__.py` соответствующих папок.
2. **Pydantic v2** используется через `model_config = {"from_attributes": True}`.
3. **SQLAlchemy 2.0 + async** — все запросы через `AsyncSession`.
4. **Репозитории** полностью изолированы, что облегчает тестирование и поддержку.
5. **FastAPI**: CRUD через эндпойнты `/people` (GET, POST, PUT, DELETE).



