## Учебный пример создания таблицы SQLAlchemy + PostgreSQL (async)

### Структура проекта

```
project/
│── docker-compose.yml
│── .env
│── database.py
│── models_person.py
│── load_data.py
│── people.json

```

---

### 1.Docker: PostgreSQL (async)

`docker-compose.yml`

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

---

### 2. .env — переменные окружения

Создайте `.env`:

```
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydb
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
```

---

## 3. Установка зависимостей

```bash
pip install sqlalchemy[asyncio] asyncpg python-dotenv
```

---

### 4. Async SQLAlchemy + загрузка .env

`database.py`

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

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ------------ устаревший синтаксис ---------------

# engine = create_engine(DB_URL)
# 
# SessionLocal = sessionmaker(
#     bind=engine,           # ← вот так
#     autocommit=False,
#     autoflush=False,
# )

# ------------ новый синтаксис ---------------

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
```

---

### 5. Модель `Person`

`models_person.py`

Устаревшая версия:

```python
from sqlalchemy import Column, Integer, String
from database import Base

class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    email = Column(String, unique=True)
```

Новая версия:

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from database import Base


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, unique=True)
```
---

### 6. Файл `people.json`

`people.json`

```json
[
  { "name": "Alice", "age": 30, "email": "alice@example.com" },
  { "name": "Bob", "age": 25, "email": "bob@example.com" },
  { "name": "Charlie", "age": 35, "email": "charlie@example.com" }
]
```

---

### 7. Создание БД и загрузка JSON

`load_data.py`

⚠️ ВАЖНО!!!
К моменту создания / удаления таблиц 
```python
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
```
должны быть импортированы ВСЕ модели!

```python
import asyncio
import json
from database import engine, AsyncSessionLocal, Base
from models_person import Person


async def init_db():
    async with engine.begin() as conn:
        # На время разработки: очищаем и создаём таблицы
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def load_people_from_json(json_file: str):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for item in data:
                person = Person(
                    name=item["name"],
                    age=item.get("age"),
                    email=item.get("email")
                )
                session.add(person)

        # await session.commit()


async def main():
    await init_db()
    await load_people_from_json("people.json")


if __name__ == "__main__":
    asyncio.run(main())
```

Здесь 
```python
async with session.begin():
    ...

``` 
контекстный менеджер, который автоматически:
* коммитит всё, что внутри него не вызвало ошибку (`commit()`)
* и немедленно откатывает изменения БД назад, если была ошибка (`rollback()`):

```python
await session.begin()
try:
    ...
    await session.commit()
except:
    await session.rollback()
    raise
``` 

---

### 8. Управляющий модуль `main.py`

```python
import asyncio
from sqlalchemy import select, func

from database import AsyncSessionLocal
from models_person import Person
from load_data import load_people_from_json, init_db

# ------------ устаревший синтаксис ---------------

# async def is_table_empty() -> bool:
#     async with AsyncSessionLocal() as session:
#         result = await session.execute(select(func.count()).select_from(Person))
#         count = result.scalar()
#         return count == 0


# async def get_people():
#     async with AsyncSessionLocal() as session:
#         result = await session.execute(select(Person))
#         return result.scalars().all()

# ------------ новый синтаксис ---------------

async def is_table_empty() -> bool:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(Person)
        )
        return count == 0


async def get_people():
    async with AsyncSessionLocal() as session:
        return await session.scalars(select(Person))


async def main():
    await init_db()

    if await is_table_empty():
        print("Таблица пуста. Загружаем people.json ...")
        await load_people_from_json("people.json")
    else:
        print("Таблица уже содержит данные.")

    people = await get_people()

    print("\nСодержимое таблицы people:")
    for p in people:
        print(f"{p.id}: {p.name}, {p.age}, {p.email}")


if __name__ == "__main__":
    asyncio.run(main())

```

🔹 `select` — это SQL-конструктор.

Создаёт запросы типа:
```
select(Person)
select(func.count())
```

🔹 `func` — прокси-доступ к SQL-функциям (`COUNT`, `SUM`, `MAX`, `NOW()`, …)

🔹 `people` — это объект типа `ScalarResult[Person]` (что-то вроде списка ORM объектов Person).

🔹 `session.scalar()` — возвращает одно скалярное значение

🔹 `session.scalars()` — возвращает итератор ORM-объектов (или итератор скалярных значений, если колонка одна).

---

### 9. Запуск

```bash
docker compose up 
```

Запускаем `main.py`.

Должно быть что-то вроде:

```python
# Содержимое таблицы people:
# 1: Alice, 30, alice@example.com
# 2: Bob, 25, bob@example.com
# 3: Charlie, 35, charlie@example.com
# 
# Process finished with exit code 0
```