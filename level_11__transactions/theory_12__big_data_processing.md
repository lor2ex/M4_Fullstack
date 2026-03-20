## Общая идея 

* Не использовать метод `.all()`, который ведёт к перегрузке памяти
* А обрабатывать результат выборки по частям: итерация / пачки

### Классический SQLAlchemy (sync)

| Подход                          | Память                  | Когда использовать                              | Пример кода (2024–2026 стиль)                                 |
|-------------------------------|--------------------------|--------------------------------------------------|----------------------------------------------------------------|
| `.limit() + .offset()`        | низкая (по странице)     | Веб-пагинация, API с page/size                   | `query.limit(100).offset(300)`                                 |
| `yield_per(n)`                | средняя (буфер n строк)  | Обработка/экспорт больших данных                 | `for obj in q.yield_per(2000): ...`                            |
| `yield_per() + execution_options(stream_results=True)` | низкая-средняя | PostgreSQL, MySQL (server-side cursor)           | `.execution_options(yield_per=5000, stream_results=True)`      |
| Core → `conn.execute().fetchmany(size)` | низкая                | Максимальная производительность, без ORM         | `for chunk in result.fetchmany(5000): ...`                     |
| `chunksize` в `pandas.read_sql()` | средняя              | Экспорт в DataFrame                              | `pd.read_sql(query, con, chunksize=10000)`                     |


```python
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine("postgresql+psycopg2://...")

# Вариант 1 — yield_per (самый частый для ORM)
with Session(engine) as session:
    q = select(User).execution_options(yield_per=5000)
    for user in session.scalars(q):           # или session.execute(q).scalars()
        process(user)                         # курсор "держит" ≈ 5000 объектов, но обработка идёт по одному

# Вариант 2 — более явный контроль (SQLAlchemy Core)
with engine.connect() as conn:
    result = conn.execution_options(yield_per=3000, stream_results=True)\
                 .execute(select(User.id, User.name))
    
    while chunk := result.fetchmany(3000):
        for row in chunk:
            process(row)
```

1. Вариант 1: Уровень SQLAlchemy ORM
   * Компромисс между памятью и скоростью:
     * В курсоре (внутри БД) выбираются порции по 5000 строк
     * но в Python-объекты эти строки превращаются строго одно по одной

2. Вариант 2: Уровень SQLAlchemy Core
   * Это уже batch-обработка
     * Сразу в память берётся и обрабатывается "связка" в 3000 строк

### Когда что выбирать?

**Вариант 1 (ORM + `yield_per`)**

* нужна бизнес-логика
* нужны relationships / методы модели
* построчная обработка
* если грузить связи, то `selectinload` — ок, `joinedload` — опасно

**Вариант 2 (Core + `fetchmany`)**

* максимальная производительность
* строгий контроль памяти
* ETL / экспорт / агрегации
* миллионы строк
* `selectinload` и `joinedload` не для этого случая, а для ORM, но здесь широкие загрузки могут работать явно.


### async SQLAlchemy (2.0+)

В async-режиме основной способ — **`.stream()`** + `yield_per` / `stream_results`.

| Подход                                | Память                  | Комментарий                                          | Пример кода                                            |
|---------------------------------------|--------------------------|------------------------------------------------------|--------------------------------------------------------|
| `session.stream(stmt)`                | низкая                   | Рекомендуемый способ в 2.0+                          | `async for obj in await session.stream(stmt): ...`     |
| `conn.stream(stmt)`                   | низкая                   | Core-уровень, больше контроля                        | `async for row in await conn.stream(stmt): ...`        |
| `session.stream(stmt).yield_per(n)`   | средняя (буфер n)        | Явное указание размера чанка                         | `.execution_options(yield_per=4000)`                   |
| `await session.stream_scalars(stmt)`  | низкая                   | Удобно когда нужны только скаляры/модели             | `async for user in await session.stream_scalars(...):` |


```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

engine = create_async_engine("postgresql+asyncpg://...", echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Вариант 1 — рекомендуемый (ORM)
async def process_large_dataset():
    async with async_session() as session:
        stmt = select(User).execution_options(yield_per=5000)
        
        # самый удобный и читаемый способ
        async for user in await session.stream_scalars(stmt):
            await process_user(user)   # или просто process_user(user)


# Вариант 2 — Core + stream
async def export_large_table():
    async with engine.connect() as conn:
        stmt = select(User.id, User.email, User.created_at)\
               .execution_options(yield_per=10000, stream_results=True)
        
        async_result = await conn.stream(stmt)
        
        async for partition in async_result.partitions(10000):
            for row in partition:
                await save_to_file(row)   # или batch insert куда-то


# Вариант 3 — если нужен явный размер чанка (компромиссный вариант: ORM, но ближе к Core по детализации и, => по скорости)
async def heavy_processing():
    async with async_session() as session:
        stmt = (
            select(User)
            .execution_options(yield_per=3000, stream_results=True)
        )
        
        stream = await session.stream(stmt)
        async for user in stream.scalars():
            await do_expensive_work(user)
```

|                 | Вариант 1 | Вариант 2       | Вариант 3 |
| --------------- | --------- | --------------- | --------- |
| Уровень         | ORM       | Core            | ORM       |
| Тип данных      | `User`    | `Row`           | `User`    |
| Реальный батч   | ❌         | ✅               | ❌         |
| Контроль памяти | косвенный | **жёсткий**     | косвенный |
| `selectinload`  | ✅         | ❌               | ✅         |
| JOIN’ы          | через ORM | вручную         | через ORM |
| Скорость        | хорошая   | **макс.**       | хорошая   |
| Рекомендуемость | ⭐⭐⭐⭐      | ⭐⭐⭐⭐⭐ (для ETL) | ⭐⭐⭐       |

Для `joinedload()` ситуация аналогичная — возможен, но опасен

* joinedload делает один большой JOIN
* создаёт дубли объектов
* ломает стриминг (yield_per или stream_scalars)
* память может взлететь
* не рекомендуется для больших наборов / 1-to-many / many-to-many
