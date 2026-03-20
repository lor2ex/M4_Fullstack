### 1. Проверка, есть ли данные в таблицах (`is_tables_empty`)

```python
async def is_tables_empty() -> bool:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Book))
        return count == 0
```

**Что делает:**

* Создаётся async сессия с базой.
* Выполняется `SELECT COUNT(*) FROM books`.
* `session.scalar()` возвращает **одно значение** (число строк).
* Возвращает `True`, если таблица `books` пустая.

**Зачем нужно:**

* Используется при инициализации данных (`init_all_data`) — чтобы не загружать книги дважды.

---

### 2. Получение списка книг (`list_books`)

```python
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
```

**Разбор:**

* `select(Book)` выбирает все книги.
* `result.scalars().all()` возвращает список объектов `Book` (ORM-объекты SQLAlchemy).
* Далее строится **словарь для каждого объекта**, включающий:

  * Простейшие поля книги (`id`, `title`, `author_id`, …)
  * **Many-to-Many**: `genre_ids = [g.id for g in b.genres]`
    — вытаскиваем только ID жанров.
  * **One-to-One**: `detail` формируется из `BookDetail`, если она есть.
* Итог: **готовый JSON-подобный список**, который можно отдать через API.

---

### 3. Создание книги (`create_book`)

```python
async def create_book(data) -> Book:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # синхронизация sequence
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
```

**Объяснение по шагам:**

1. `async with session.begin()` — открывает транзакцию в контекстном менеджере; 
    * тем самым гарантирует, что после выхода из контекстного менеджера все изменения будут 
      * либо сохранены, 
      * либо откатятся.
      
2. **Синхронизация sequence** (актуально для PostgreSQL):

   * Требуется, после сброса данных (наш случай).
   * Команда `setval('books_id_seq', MAX(id))` гарантирует, что следующий `id` не будет конфликтовать.
3. Создаём объект `Book` и добавляем его в сессию.
4. `await session.flush()` — принудительно отправляет изменения в базу, чтобы SQLAlchemy знал `id` книги,   
    когда **транзакция ещё не закоммичена**.

---

#### 3.1 Many-to-Many жанры

```python
if data.genre_ids:
    result = await session.execute(
        select(Genre).where(Genre.id.in_(data.genre_ids))
    )
    book.genres = result.scalars().all()
```

* Берём жанры по переданным `genre_ids`.
* Связываем их с книгой через `book.genres`.
* SQLAlchemy автоматически добавляет записи в таблицу ассоциации `book_genres`.

---

#### 3.2 One-to-One детали книги

```python
if data.detail:
    book.detail = BookDetail(
        summary=data.detail.summary,
        page_count=data.detail.page_count
    )
```

* Если пришли данные `detail`, создаём объект `BookDetail`.
* `book.detail = ...` устанавливает связь One-to-One.
* SQLAlchemy присваивает `book_id` автоматически.

---

### 3. Удаление книги (`delete_book`)

```python
async def delete_book(book_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            book = await session.get(Book, book_id)
            if not book:
                return False
            await session.delete(book)
        return True
```

* Ищем книгу по `id`.
* Если есть — удаляем.
* Благодаря `cascade="all, delete-orphan"` в моделях:

  * One-to-One `BookDetail` удаляется автоматически.
  * Many-to-Many `BookGenre` записи в таблице ассоциации тоже удаляются.
* Возвращаем `True`/`False` в зависимости от результата.

---

### 4. Основные принципы репозитория

1. **async сессии** — все методы используют `AsyncSessionLocal()`.
2. **Транзакции** — `async with session.begin()` гарантирует целостность данных.
3. **Связи**:

   * **1:N** — через `author_id`.
   * **M:N** — через `book.genres` (таблица ассоциации `book_genres`).
   * **1:1** — через `book.detail`.
4. **Сериализация** — для `list_books()` ORM-объекты превращаются в словари, готовые для JSON.
5. **Flush vs Commit**:

   * `flush()` — отправляет данные в базу, но транзакция ещё не завершена.
   * `commit()` — фиксация изменений (в асинхронном `session.begin()` выполняется автоматически при выходе из блока).


