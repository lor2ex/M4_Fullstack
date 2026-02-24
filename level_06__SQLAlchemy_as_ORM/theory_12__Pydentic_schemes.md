## Соотношение Pydantic-схем и моделей SQLAlchemy на примере нашего проекта.

## 1. Создание и чтение книги (`Create` vs `Read`)

Схемы разделены на **Create** и **Read**:

* **Create** (`BookCreate`, `BookDetailCreate`) — для входящих данных (когда создаётся объект через API).
* **Read** (`BookRead`, `BookDetailRead`, `AuthorRead`, `GenreRead`) — для выхода (когда отдаём данные клиенту).

Пример:

```python
class BookDetailCreate(BaseModel):
    summary: str | None = None
    page_count: int | None = None
```

* `summary` и `page_count` необязательны (`None` по умолчанию).
* Используется для создания деталей книги.

```python
class BookDetailRead(BaseModel):
    id: int
    summary: str | None
    page_count: int | None

    model_config = {"from_attributes": True}
```

* `id` появляется только при чтении, так как при записи `id` генерирует сама база (`autoincrement` по умолчанию).
* `model_config = {"from_attributes": True}`:
  * позволяет Pydantic автоматически считывать данные **из атрибутов объекта ORM** 
  * (`book.detail.summary` и т.д.), а не только из словарей.

---

## 2. Вложенные объекты (One-to-One)

Пример: `Book` → `BookDetail` (One-to-One)

```python
class BookCreate(BaseModel):
    title: str
    year_published: int | None = None
    is_deleted: bool = False
    author_id: int
    genre_ids: list[int] | None = None
    detail: BookDetailCreate | None = None
```

* Поле `detail` — вложенный объект `BookDetailCreate`.
* Таким образом, при создании книги можно одновременно передать детали книги.
* `| None` — значит, детали необязательны.

Для чтения:

```python
class BookRead(BaseModel):
    id: int
    title: str
    author_id: int
    year_published: int | None
    is_deleted: bool
    genre_ids: list[int] | None
    detail: BookDetailRead | None

    model_config = {"from_attributes": True}
```

* `detail` теперь `BookDetailRead` — читаемый объект.
* `genre_ids` — список ID жанров, чтобы не передавать всю модель Genre (можно для клиента ограничить данные).

---

## 3. Маппинг Many-to-Many (книги ↔ жанры)

```python
genre_ids: list[int] | None = None
```

* Для **создания книги** мы передаём ТОЛЬКО список `genre_ids` (а не всю модель `Genre`).
* При чтении (`BookRead`) поле `genre_ids` формируется из `book.genres`:

```python
genre_ids=[g.id for g in book.genres] if book.genres else []
```

* Это удобный способ показать связь Many-to-Many клиенту без передачи всех атрибутов жанров.

---

## 4. One-to-Many (Автор ↔ Книги)

```python
class AuthorRead(BaseModel):
    id: int
    name: str
    book_ids: list[int] = []

    model_config = {"from_attributes": True}
```

* `book_ids` — список ID книг автора.
* Для сериализации используется доступ к `author.books`, затем извлекаются `id`:

```python
book_ids = [b.id for b in author.books]
```

---

## 5. Универсальная функция преобразования ORM → Pydantic
(сериализация объекта Book со сложными реляционными связями — все 3 типа в одной функции!)

Т.е. функция `book_to_read` объединяет 4 таблицы БД в одну Pydantic схему.

```python
def book_to_read(book: Book) -> BookRead:
    return BookRead(
        id=book.id,
        title=book.title,
        author_id=book.author_id,
        year_published=book.year_published,
        is_deleted=book.is_deleted,
        genre_ids=[g.id for g in book.genres] if book.genres else [],
        detail=BookDetailRead.model_validate(book.detail) if book.detail else None
    )
```

* `model_validate` (новое название вместо `from_orm`) позволяет создать Pydantic-схему из объекта SQLAlchemy.
* Функция формирует `BookRead` с вложенными связями и списками ID.

---

## 6. Ключевые моменты

1. **Разделение схем** — для безопасности и удобства API (`Create`/`Read`).
2. **Вложенные схемы** — для One-to-One (`detail`) или даже вложенных списков (Many-to-Many можно расширить).
3. **ID вместо объектов** — при Many-to-Many удобно отдавать клиенту только идентификаторы, чтобы не перегружать ответ.
4. **`model_config = {"from_attributes": True}`** — интеграция с SQLAlchemy ORM.
5. **Универсальная функция преобразования** — облегчает сериализацию объектов с вложенными связями.

