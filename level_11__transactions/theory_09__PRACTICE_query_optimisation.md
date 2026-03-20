# Оптимизация запросов в проекте CRUD_SQLAlchemy_FastAPI

## 1. Добавим эндпойнты

* `/authors/{author_id}/books/` — все книги одного автора (1:N)
* `/genres/{genre_id}/books/` — все книги одного жанра (M:N)

### Репозиторий

Добавим методы:

```python
from sqlalchemy.orm import selectinload

from app.db.models.books import Book, Genre, BookDetail, BookGenre


class BookRepository:

    # ... существующие методы

    @staticmethod
    async def list_books_by_author(author_id: int) -> list[Book]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Book)
                .where(Book.author_id == author_id)
                # Загрузка жанров и деталей, чтобы избежать N+1
                .options(
                    selectinload(Book.genres),
                    selectinload(Book.detail)
                )
            )
            return result.scalars().all()

    @staticmethod
    async def list_books_by_genre(genre_id: int) -> list[Book]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Book)
                .where(Book.genres.any(Genre.id == genre_id))
                .options(
                    selectinload(Book.genres),  # ← возвращает жанры
                    selectinload(Book.detail)  # если нужно
                )

            )
            return result.scalars().all()
```

⚠️ Важная деталь:

* `selectinload(Book.genres)` → SQLAlchemy сделает **один дополнительный запрос**,
  * чтобы загрузить все жанры для всех книг сразу, 
  * вместо отдельного запроса на каждый объект (`N+1`).
* `selectinload(Book.detail)` → аналогично для One-to-One.
  * делается один запрос, чтобы подгрузить все детали для всех книг сразу

---

### Эндпойнты FastAPI

```python
from fastapi import APIRouter
from typing import List
from app.db.models.books import BookRead, book_to_read
from app.db.repository.books import BookRepository

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/by_author/{author_id}", response_model=List[BookRead])
async def get_books_by_author(author_id: int):
    books = await BookRepository.list_books_by_author(author_id)
    return [book_to_read(b) for b in books]

@router.get("/by_genre/{genre_id}", response_model=List[BookRead])
async def get_books_by_genre(genre_id: int):
    books = await BookRepository.list_books_by_genre(genre_id)
    return [book_to_read(b) for b in books]
```

---

## 2. Демонстрация преимущества `eager loading` перед `lazy loading` с его N+1

В проекте использован `asyncpg`, поэтому классического «N+1 запросов»  
(1 запрос на список + по 1 запросу на каждую книгу) здесь **просто не бывает** —  
потому что он запрещён на уровне библиотеки.

Поэтому код ниже просто продемонстрирует 3 сценария работы:
1. Основной запрос Книг без подгрузки связанных объектов
2. Основной запрос Книг с подгрузкой только Жанров
3. Основной запрос Книг с подгрузкой и Жанров, и детализации.

Под скрипт создаём отдельный модуль в корне проекта: `benchmark_n_plus_1.py`

```python
import asyncio
import time
from sqlalchemy import select, event
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.books import Book, Genre  # подкорректируй импорт
from app.db import AsyncSessionLocal

# ────────────────────────────────────────────────
# Счётчик запросов (работает через sync_engine)
# ────────────────────────────────────────────────
def create_query_counter(engine):
    query_count = [0]

    def increment_count(*args, **kwargs):
        query_count[0] += 1

    event.listen(engine.sync_engine, "before_cursor_execute", increment_count)

    def get_and_reset():
        count = query_count[0]
        query_count[0] = 0
        return count

    return get_and_reset


# ────────────────────────────────────────────────
# Версия 1: Ничего не eager-load → genres/detail пустые, запросов минимум
# ────────────────────────────────────────────────
async def version_no_load(session: AsyncSession, genre_id: int):
    result = await session.execute(
        select(Book).where(Book.genres.any(Genre.id == genre_id))
    )
    books = result.scalars().all()

    for book in books:
        # НЕ трогаем .genres и .detail → не крашится
        print(f"Book {book.title:<30} | genres: не загружены ({len(book.genres)}), detail: не загружен")

    return books


# ────────────────────────────────────────────────
# Версия 2: Только genres eager → +1 запрос на жанры
# ────────────────────────────────────────────────
async def version_genres_only(session: AsyncSession, genre_id: int):
    result = await session.execute(
        select(Book)
        .where(Book.genres.any(Genre.id == genre_id))
        .options(selectinload(Book.genres))
    )
    books = result.scalars().all()

    for book in books:
        print(f"Book {book.title:<30} | genres: {len(book.genres):2} шт, detail: не загружен")

    return books


# ────────────────────────────────────────────────
# Версия 3: Полный eager (genres + detail) → +2 запроса, всё загружено
# ────────────────────────────────────────────────
async def version_full_load(session: AsyncSession, genre_id: int):
    result = await session.execute(
        select(Book)
        .where(Book.genres.any(Genre.id == genre_id))
        .options(
            selectinload(Book.genres),
            selectinload(Book.detail)
        )
    )
    books = result.scalars().all()

    for book in books:
        detail_pages = book.detail.page_count if book.detail else "нет"
        print(f"Book {book.title:<30} | genres: {len(book.genres):2} шт, detail pages: {detail_pages}")

    return books


# ────────────────────────────────────────────────
# Бенчмарк
# ────────────────────────────────────────────────
async def benchmark(genre_id: int = 1):
    engine = AsyncSessionLocal.kw["bind"]
    counter = create_query_counter(engine)

    versions = [
        ("No load (genres/detail пустые)", version_no_load),
        ("Only genres loaded", version_genres_only),
        ("Full load (genres + detail)", version_full_load),
    ]

    for name, func in versions:
        print(f"\n=== {name} ===")
        async with AsyncSessionLocal() as session:
            start = time.perf_counter()
            await func(session, genre_id)
            elapsed = time.perf_counter() - start
            q = counter()
            print(f"Time: {elapsed:.4f} sec | Queries: {q}")


if __name__ == "__main__":
    asyncio.run(benchmark(genre_id=1))  # подставь реальный genre_id с данными
```

Запускаем его как обычный файл и получаем что-то вроде этого:

```
=== No load (genres/detail пустые) ===
Book War and Peace                  | genres: не загружены (0), detail: не загружен
Book Anna Karenina                  | genres: не загружены (0), detail: не загружен
Book Crime and Punishment           | genres: не загружены (0), detail: не загружен
Book The Idiot                      | genres: не загружены (0), detail: не загружен
Book Pride and Prejudice            | genres: не загружены (0), detail: не загружен
Book Emma                           | genres: не загружены (0), detail: не загружен
Time: 0.2380 sec | Queries: 3

=== Only genres loaded ===
Book War and Peace                  | genres:  2 шт, detail: не загружен
Book Anna Karenina                  | genres:  2 шт, detail: не загружен
Book Crime and Punishment           | genres:  2 шт, detail: не загружен
Book The Idiot                      | genres:  2 шт, detail: не загружен
Book Pride and Prejudice            | genres:  2 шт, detail: не загружен
Book Emma                           | genres:  2 шт, detail: не загружен
Time: 0.0084 sec | Queries: 4

=== Full load (genres + detail) ===
Book War and Peace                  | genres:  2 шт, detail pages: 1225
Book Anna Karenina                  | genres:  2 шт, detail pages: 864
Book Crime and Punishment           | genres:  2 шт, detail pages: 671
Book The Idiot                      | genres:  2 шт, detail pages: 656
Book Pride and Prejudice            | genres:  2 шт, detail pages: 432
Book Emma                           | genres:  2 шт, detail pages: 474
Time: 0.0052 sec | Queries: 4

```

### Что означают три варианта на практике

| Вариант                  | Запросов | Время (в твоём примере) | Что реально происходит в базе | Когда это полезно / вредно |
|--------------------------|----------|--------------------------|--------------------------------|-----------------------------|
| No load                  | 3        | 0.0388 сек              | Только один запрос на книги. Genres и detail **никогда** не загружаются | Полезно, если жанры/детали вообще не нужны в этом эндпоинте |
| Only genres loaded       | 4        | 0.0078 сек              | 1 запрос на книги + 1 запрос на все жанры сразу (IN по book_ids) | Идеально, если нужны только жанры, detail не нужен |
| Full load (genres + detail) | 4     | 0.0052 сек              | 1 запрос на книги + 1 на жанры + 1 на detail (иногда + служебный) | Самый удобный для большинства API-ответов, где отображаются и жанры, и summary/страницы |

**Выводы:**

- Время **падает** в 5–7 раз при добавлении eager loading → потому что нет скрытых блокирующих операций
  - то есть при первый запрос пытается лениво подгрузить и жанры и дополнения (дольше всех)
  - второй запрос не тратит время на ленивые попытки и грузит жанры асинхронно (среднее время)
  - последний - вообще не тратит время - просто грузит (самый быстрый)
- Количество запросов **растёт всего на 1–2**, а не на N (как было бы в синхронном режиме)
- Разница между "Only genres" и "Full load" почти нулевая (4 запроса в обоих случаях) → S
  - QLAlchemy часто объединяет/оптимизирует такие запросы


  