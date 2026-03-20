## Вносим изменения в проект

### Изменённая структура проекта

```
/project/
├── app
│   ├── db
│   │   ├── __init__.py
│   │   ├── initial_data.py
│   │   ├── models
│   │   │   ├── __init__.py
│   │   │   ├── books.py
│   │   │   └── person.py
│   │   └── repository
│   │       ├── __init__.py
│   │       ├── books.py
│   │       └── person.py
│   ├── main.py
│   └── routers
│       ├── __init__.py
│       ├── books.py
│       └── people.py
├── books.json
├── docker-compose.yml
├── people.json
└── requirements.txt
```

---

### 1. `app/db/models/books.py` — модели (SQLAlchemy 2.0)

```python
# app/db/models/books.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, Text, Boolean, Table
from pydantic import BaseModel
from app.db import Base

# =============================
#   ORM МОДЕЛИ
# =============================

# ---------- Автор ----------
class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # связь 1:N с книгами
    books: Mapped[list["Book"]] = relationship(
        back_populates="author",
        lazy="selectin"
    )


# ---------- Жанр ----------
class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # связь M:N с книгами
    books: Mapped[list["Book"]] = relationship(
        back_populates="genres",
        secondary="book_genres",
        lazy="selectin"
    )


# ---------- Ассоциация книги ↔ жанры ----------
class BookGenre(Base):
    __tablename__ = "book_genres"

    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


# ---------- Книга ----------
class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year_published: Mapped[int | None] = mapped_column(Integer)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # связь с автором (1:N)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped["Author"] = relationship(
        back_populates="books",
        lazy="selectin"
    )

    # many-to-many с жанрами
    genres: Mapped[list["Genre"]] = relationship(
        back_populates="books",
        secondary="book_genres",
        lazy="noload",
        cascade="all, delete"
    )

    # one-to-one
    detail: Mapped["BookDetail"] = relationship(
        back_populates="book",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )


# ---------- Детализация книги (One-to-One) ----------
class BookDetail(Base):
    __tablename__ = "book_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)

    book: Mapped["Book"] = relationship(
        back_populates="detail",
        lazy="selectin"
    )


# =============================
#   Pydantic-схемы
# =============================

class BookDetailCreate(BaseModel):
    summary: str | None = None
    page_count: int | None = None


class BookDetailRead(BaseModel):
    id: int
    summary: str | None
    page_count: int | None

    model_config = {"from_attributes": True}


class BookCreate(BaseModel):
    title: str
    year_published: int | None = None
    is_deleted: bool = False
    author_id: int
    genre_ids: list[int] | None = None
    detail: BookDetailCreate | None = None


class BookRead(BaseModel):
    id: int
    title: str
    year_published: int | None
    is_deleted: bool
    author_id: int
    genre_ids: list[int] | None
    detail: BookDetailRead | None

    model_config = {"from_attributes": True}

def book_to_read(book: Book) -> BookRead:
    return BookRead(
        id=book.id,
        title=book.title,
        author_id=book.author_id,
        year_published=book.year_published,
        is_deleted=book.is_deleted,
        genre_ids=[g.id for g in book.genres] if book.genres else [],
        detail=BookDetailRead.model_validate(book.detail) if book.detail else None    )

class AuthorRead(BaseModel):
    id: int
    name: str
    book_ids: list[int] = []

    model_config = {"from_attributes": True}


class GenreRead(BaseModel):
    id: int
    name: str
    book_ids: list[int] = []

    model_config = {"from_attributes": True}

```

---

### 2. Обновите `app/db/models/__init__.py` — экспорт моделей

```python
from .person import Person, PersonCreate, PersonRead  # эти модели уже есть

from .books import (                                  # добавляем новые модели
    Author, Genre, Book, BookDetail, BookGenre, book_to_read

)

# __all__ погоды не делает (достаточно одних импортов), но читабельность улучшает
__all__ = [
    "Person", "PersonCreate", "PersonRead",
    "Author", "Genre", "Book", "BookDetail", "BookGenre", "book_to_read"
]
```

( `__all__` опционален, но полезен — добавил для явности )

---

### 3. `app/db/initial_data.py` — загрузчик `books.json`, `persin.json` и обновлённый `init_db`

```python
import json
from app.db import engine, Base
from app.db.repository.person import PersonRepository
from app.db.models.books import Author, Genre, Book, BookDetail
from app.db import AsyncSessionLocal

# ---------------------------------------------------------
# INIT DB: DROP ALL → CREATE ALL
# ---------------------------------------------------------

from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        # удаляем таблицы с зависимостями через raw SQL
        await conn.execute(text("DROP TABLE IF EXISTS book_genres CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS book_details CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS books CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS authors CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS genres CASCADE"))
        # создаём все таблицы ORM
        await conn.run_sync(Base.metadata.create_all)



# ---------------------------------------------------------
# LOAD PEOPLE
# ---------------------------------------------------------
async def load_people_from_json(json_file: str):
    with open(json_file, "r", encoding="utf-8") as f:
        people = json.load(f)

    for item in people:
        await PersonRepository.create_person(
            name=item["name"],
            age=item.get("age"),
            email=item.get("email"),
        )


# ---------------------------------------------------------
# LOAD BOOKS (authors, genres, books, book_details)
# ---------------------------------------------------------
async def load_books_from_json(json_file: str):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    authors = data["authors"]
    genres = data["genres"]
    books = data["books"]
    details = data["book_details"]

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        async with session.begin():

            # -------- AUTHORS --------
            for a in authors:
                session.add(Author(
                    id=a["id"],
                    name=a["name"]
                ))

            # -------- GENRES --------
            for g in genres:
                session.add(Genre(
                    id=g["id"],
                    name=g["name"]
                ))

            await session.flush()  # применяем вставки, чтобы id были доступны

            # -------- BOOKS --------
            for b in books:
                book = Book(
                    id=b["id"],
                    title=b["title"],
                    author_id=b["author_id"],
                    year_published=b.get("year_published"),
                    is_deleted=b.get("is_deleted", False)
                )
                session.add(book)
                await session.flush()

                # many-to-many genres
                book.genres = [
                    await session.get(Genre, gid) for gid in b.get("genre_ids", [])
                    if await session.get(Genre, gid) is not None
                ]

                session.add(book)

            await session.flush()

            # -------- BOOK DETAILS --------
            for d in details:
                book = await session.get(Book, d["book_id"])
                if book:
                    book.detail = BookDetail(
                        summary=d.get("summary"),
                        page_count=d.get("page_count")
                    )

# ---------------------------------------------------------
# Full initialization call (optional helper)
# ---------------------------------------------------------
async def init_all_data():
    await init_db()
    await load_people_from_json("people.json")
    await load_books_from_json("books.json")

```

---

### 4. `app/db/__init__.py`

Оставляем без изменений

---

### 5. `app/db/repositories/books.py` — репозиторий CRUD

```python
from sqlalchemy import select, func, text
from app.db import AsyncSessionLocal
from app.db.models.books import Book, Genre, BookDetail

class BookRepository:

    @staticmethod
    async def is_tables_empty() -> bool:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(select(func.count()).select_from(Book))
            return count == 0

    @staticmethod
    async def list_books() -> list[dict]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Book))
            books = result.scalars().all()
            return [
                {
                    "id": b.id,
                    "title": b.title,
                    "author_id": b.author_id,
                    "year_published": b.year_published,
                    "is_deleted": b.is_deleted,
                    "genre_ids": [g.id for g in b.genres],
                    "detail": {
                        "id": b.detail.id if b.detail else None,
                        "summary": b.detail.summary if b.detail else None,
                        "page_count": b.detail.page_count if b.detail else None
                    }
                }
                for b in books
            ]

    @staticmethod
    async def create_book(data) -> Book:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # синхронизируем sequence автоматически
                await session.execute(
                    text("SELECT setval('books_id_seq', (SELECT MAX(id) FROM books))")
                )

                book = Book(
                    title=data.title,
                    author_id=data.author_id,
                    year_published=data.year_published,
                    is_deleted=False
                )
                session.add(book)
                await session.flush()

                # genres
                if data.genre_ids:
                    result = await session.execute(
                        select(Genre).where(Genre.id.in_(data.genre_ids))
                    )
                    book.genres = result.scalars().all()

                # details
                if data.detail:
                    book.detail = BookDetail(
                        summary=data.detail.summary,
                        page_count=data.detail.page_count
                    )
            return book

    @staticmethod
    async def delete_book(book_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                book = await session.get(Book, book_id)
                if not book:
                    return False
                await session.delete(book)
            return True

```

**`app/db/repository/__init__.py`**

```python
from .person import PersonRepository  # было
from .books import BookRepository     # добавляем
```

---

### 6. `app/routers/books.py` — FastAPI роутер (эндпойнты)

```python
from fastapi import APIRouter, HTTPException
from typing import List
from app.db.models.books import BookCreate, BookRead, book_to_read
from app.db.repository.books import BookRepository

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/", response_model=List[BookRead])
async def read_books():
    return await BookRepository.list_books()

@router.post("/books/", response_model=BookRead)
async def add_book(data: BookCreate):
    book = await BookRepository.create_book(data)
    return book_to_read(book)

@router.delete("/{book_id}")
async def delete_book(book_id: int):
    ok = await BookRepository.delete_book(book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book was deleted"}

```

---

### 7. Интеграция в `main.py` (lifespan)


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

### 8. `books.json`

Не забываем добавить в корень проекта

---

### 9. Примеры использования (через `/docs`)

Просто смотрим [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

⚠️ При добавлении книги id автора и жанр сделать равными 1 !!!