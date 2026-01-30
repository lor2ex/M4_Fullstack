from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

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
            stmt = (
                select(Book)
                .options(
                    selectinload(Book.genres),
                    selectinload(Book.detail),
                    # selectinload(Book.author)  # раскомментируйте, если нужен автор
                )
            )
            result = await session.execute(stmt)
            books = result.unique().scalars().all()

            # отладка (можно удалить позже)
            print(f"Найдено книг: {len(books)}")
            for b in books[:3]:  # первые 3 для примера
                genres_str = [g.id for g in b.genres] if b.genres else []
                print(f"Книга {b.title}: жанров = {len(genres_str)} → {genres_str}")

            return [
                {
                    "id": b.id,
                    "title": b.title,
                    "author_id": b.author_id,
                    "year_published": b.year_published,
                    "is_deleted": b.is_deleted,
                    "genre_ids": [g.id for g in b.genres],
                    "detail": (
                        {
                            "id": b.detail.id,
                            "summary": b.detail.summary,
                            "page_count": b.detail.page_count,
                        }
                        if b.detail is not None else None
                    )
                }
                for b in books
            ]

    @staticmethod
    async def create_book(data) -> Book:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Опционально: синхронизация sequence (можно убрать, если не было проблем с id)
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
                await session.flush()  # ← важно, чтобы id сгенерировался

                # genres
                if data.genre_ids:
                    stmt = select(Genre).where(Genre.id.in_(data.genre_ids))
                    result = await session.execute(stmt)
                    found_genres = result.scalars().all()

                    # Проверяем, что нашли все запрошенные жанры (опционально, но полезно)
                    found_ids = {g.id for g in found_genres}
                    missing = set(data.genre_ids) - found_ids
                    if missing:
                        raise ValueError(f"Не найдены жанры с id: {missing}")

                    book.genres = found_genres

                # details
                if data.detail:
                    book.detail = BookDetail(
                        summary=data.detail.summary,
                        page_count=data.detail.page_count
                    )
                    # await session.flush()   # можно добавить, если хочется сразу id у detail

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
