import json
from sqlalchemy import select
from app.db import engine, Base
from app.db.repository.person import PersonRepository
from app.db.models.books import Author, Genre, Book, BookDetail
from app.db import AsyncSessionLocal
from typing import List
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
async def load_books_from_json(json_file: str = "books.json"):
    """
    Загружает данные из books.json:
    - Авторы (без указания id → база генерирует)
    - Жанры (без id → база генерирует)
    - Книги + привязка к автору и жанрам по старым id из JSON
    - Детали книг (one-to-one)
    """
    print(f"→ Начало загрузки из {json_file}")

    # 1. Чтение JSON
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"!!! Файл {json_file} не найден")
        return
    except json.JSONDecodeError as e:
        print(f"!!! Ошибка формата JSON: {e}")
        return
    except Exception as e:
        print(f"!!! Ошибка при чтении файла: {type(e).__name__} → {e}")
        return

    authors_data: List[dict] = data.get("authors", [])
    genres_data: List[dict]  = data.get("genres", [])
    books_data: List[dict]   = data.get("books", [])
    details_data: List[dict] = data.get("book_details", [])

    print(f"   Данных в JSON: авторов={len(authors_data)}, "
          f"жанров={len(genres_data)}, книг={len(books_data)}, "
          f"деталей={len(details_data)}")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            try:
                # ─── Авторы ────────────────────────────────────────────────
                authors = [Author(name=item["name"]) for item in authors_data]
                session.add_all(authors)
                await session.flush()
                print(f"   Добавлено авторов: {len(authors)}")

                # Map: старый id автора → объект Author
                author_map = {}
                for old_author, new_author in zip(authors_data, authors):
                    old_id = old_author.get("id")
                    if old_id is not None:
                        author_map[old_id] = new_author

                # ─── Жанры ─────────────────────────────────────────────────
                genres = [Genre(name=item["name"]) for item in genres_data]
                session.add_all(genres)
                await session.flush()
                print(f"   Добавлено жанров: {len(genres)}")

                # Map: старый id жанра → объект Genre
                genre_map = {}
                for old_genre, new_genre in zip(genres_data, genres):
                    old_id = old_genre.get("id")
                    if old_id is not None:
                        genre_map[old_id] = new_genre

                # ─── Книги + связи ─────────────────────────────────────────
                created_books = []  # список в порядке создания — ключевой момент

                processed_books = 0
                for book_item in books_data:
                    old_author_id = book_item.get("author_id")
                    author = author_map.get(old_author_id)

                    if not author:
                        print(
                            f"   ! Автор с id={old_author_id} не найден → пропускаем книгу '{book_item.get('title')}'")
                        continue

                    book = Book(
                        title=book_item["title"],
                        author=author,
                        year_published=book_item.get("year_published"),
                        is_deleted=book_item.get("is_deleted", False)
                    )
                    session.add(book)
                    await session.flush()  # получаем book.id

                    created_books.append(book)  # сохраняем объект в правильном порядке

                    # Привязка жанров (оставляем как было)
                    genre_ids_old = book_item.get("genre_ids", [])
                    book.genres = [
                        genre_map[old_gid]
                        for old_gid in genre_ids_old
                        if old_gid in genre_map
                    ]

                    attached_count = len(book.genres)
                    expected_count = len(genre_ids_old)
                    print(f"   Книга '{book.title}': "
                          f"genre_ids из JSON = {genre_ids_old} → "
                          f"привязано {attached_count}/{expected_count} жанров")

                    processed_books += 1

                print(f"   Успешно обработано книг: {processed_books}/{len(books_data)}")

                # ─── Детали книг ───────────────────────────────────────────
                book_map = {}
                for book_item, book_obj in zip(books_data, created_books):
                    old_book_id = book_item.get("id")
                    if old_book_id is not None:
                        book_map[old_book_id] = book_obj

                for detail_item in details_data:
                    old_book_id = detail_item.get("book_id")
                    book = book_map.get(old_book_id)
                    if book:
                        book.detail = BookDetail(
                            summary=detail_item.get("summary"),
                            page_count=detail_item.get("page_count")
                        )
                        print(f"   → Добавлена деталь для книги '{book.title}' (old id {old_book_id})")
                    else:
                        print(f"   ! Книга с old id={old_book_id} не найдена для детали")

                await session.commit()
                print("   Коммит успешен — все данные сохранены")

            except Exception as e:
                await session.rollback()
                print(f"!!! ОШИБКА В ТРАНЗАКЦИИ: {type(e).__name__}")
                print(str(e))
                import traceback
                traceback.print_exc()
                raise

    print("← Загрузка завершена\n")
# ---------------------------------------------------------
# Full initialization call (optional helper)
# ---------------------------------------------------------
async def init_all_data():
    await init_db()
    await load_people_from_json("people.json")
    await load_books_from_json("books.json")
