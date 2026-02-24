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
        cascade="save-update, merge, delete"
    )

    # one-to-one
    detail: Mapped["BookDetail"] = relationship(
        back_populates="book",
        uselist=False,
        cascade="save-update, merge, delete, delete-orphan",
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
    id: int | None = None
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
