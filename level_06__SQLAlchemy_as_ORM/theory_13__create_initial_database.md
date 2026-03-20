## Разбор заполнение таблиц SQLAlchemy на примере нашего мини-проекта


### 1. Инициализация базы

```python
async def init_db():
    async with engine.begin() as conn:
        # удаляем все таблицы с зависимостями
        await conn.execute(text("DROP TABLE IF EXISTS book_genres CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS book_details CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS books CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS authors CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS genres CASCADE"))

        # создаём таблицы ORM
        await conn.run_sync(Base.metadata.create_all)
```

**Что происходит:**

* Сначала удаляются таблицы в порядке, который учитывает зависимости (`CASCADE`)
  * это важно, иначе база выдаст ошибку из-за внешних ключей.
* Затем SQLAlchemy создаёт все таблицы на основе классов `Base` (`Author`, `Genre`, `Book`, `BookDetail`, `BookGenre`).

**Что здесь важно для тестирования CRUD-операций?**

* То, что при перезагрузке проекта все таблицы пересоздаются из json-файлов.

---

### 2. Загрузка людей (пример для Person)

```python
async def load_people_from_json(json_file: str):
    people = json.load(open(json_file, encoding="utf-8"))
    for item in people:
        await PersonRepository.create_person(
            name=item["name"],
            age=item.get("age"),
            email=item.get("email"),
        )
```

* Читаем JSON-файл с людьми.
* Создаём записи через репозиторий `PersonRepository.create_person`.
* Здесь нет связей с книгами, просто базовая вставка.

---

### 3. Загрузка книг и связанных сущностей

```python
async def load_books_from_json(json_file: str):
    data = json.load(open(json_file, encoding="utf-8"))

    authors = data["authors"]
    genres = data["genres"]
    books = data["books"]
    details = data["book_details"]
```

* JSON разделён на **authors**, **genres**, **books**, **book_details**.
* Сначала создаём авторов и жанры, потом книги и детали — чтобы связи через `ForeignKey` были корректны.

---

#### 3.1 Добавление авторов

```python
for a in authors:
    session.add(Author(id=a["id"], name=a["name"]))
```

* Просто создаём объекты `Author`.
* После `flush()` SQLAlchemy знает все `id`, даже если они автоинкрементные.
* Связь 1:N с книгами (`author.books`) пока не заполняется — она создаётся при добавлении книг через `author_id`.

---

#### 3.2 Добавление жанров

```python
for g in genres:
    session.add(Genre(id=g["id"], name=g["name"]))
await session.flush()
```

* Сохраняем все жанры, чтобы позже их можно было назначать книгам через Many-to-Many.
* `flush()` нужен, чтобы `session.get(Genre, gid)` мог найти жанр по `id`.

---

#### 3.3 Добавление книг

```python
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
```

* Создаём объект `Book`.
* Через `author_id` создаётся связь 1:N с `Author`.
* `flush()` нужен, чтобы объект книги получил `id` и стал доступен для присвоения деталей или жанров.

---

#### 3.4 Many-to-Many: жанры книги

```python
book.genres = [
    await session.get(Genre, gid) for gid in b.get("genre_ids", [])
    if await session.get(Genre, gid) is not None
]
```

* Для каждой книги формируем список жанров из уже существующих объектов `Genre`.
* SQLAlchemy автоматически создаст записи в таблице ассоциации `book_genres`.
* Связь Many-to-Many готова после `flush()`.

---

#### 3.5 One-to-One: детали книги

```python
for d in details:
    book = await session.get(Book, d["book_id"])
    if book:
        book.detail = BookDetail(
            summary=d.get("summary"),
            page_count=d.get("page_count")
        )
```

* Для каждой записи `BookDetail` находим соответствующую книгу по `book_id`.
* Через `book.detail = BookDetail(...)` создаётся связь One-to-One.
* SQLAlchemy автоматически присваивает `book_id` в `BookDetail` через `ForeignKey`.

---

### 4. Итог последовательности

1. Создаются **таблицы** (DROP → CREATE).
2. Загружаются авторы (`Author`) и жанры (`Genre`) — независимые таблицы.
3. Создаются книги (`Book`) с привязкой к авторам.
4. Назначаются жанры книгам (Many-to-Many) через `book.genres`.
5. Создаются детали книги (One-to-One) через `book.detail`.

> ⚡ В результате каждая книга уже содержит все связи: автор, жанры и детали. 
> Именно так и формируется объект `Book`, который потом можно сериализовать через функцию `book_to_read` 
> в Pydantic-схему `BookRead`.

