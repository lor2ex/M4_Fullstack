Разберём теорию реляционных связей между таблицами в SQLAlchemy на примере нашего мини-проекта.  

---

## 1. One-to-Many (1:N) — один ко многим

**Пример:** Автор ↔ Книги (`Author` → `Book`)

```python
# В классе Author
books: Mapped[list["Book"]] = relationship(
    back_populates="author",
    lazy="selectin"
)

# В классе Book
author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
author: Mapped["Author"] = relationship(
    back_populates="books",
    lazy="selectin"
)
```

**Объяснение:**

* Один автор может написать много книг, но каждая книга принадлежит только одному автору.
* `ForeignKey` в таблице `books` указывает на таблицу `authors`.
* `relationship` связывает объекты Python, а не только таблицы в базе.
* `back_populates` обеспечивает двустороннюю связь: можно получить книги автора (`author.books`) и автора книги (`book.author`).
* `lazy="selectin"` — стратегия загрузки: 
  * при первом обращении к связи, SQLAlchemy делает дополнительный запрос для связанных объектов.
  * это уменьшает количество отдельных запросов и предотвращает "N+1 query problem",
  * Основной запрос:
    ```sql
    SELECT books.id, books.title, books.author_id
    FROM books;
    ```
  * "Ленивый" запрос:
    ```sql
    SELECT authors.id, authors.name
    FROM authors
    WHERE authors.id IN (1, 2, 3);
    ```
---

## 2. Many-to-Many (M:N) — многие ко многим

**Пример:** Книга ↔ Жанры (`Book` ↔ `Genre`) через ассоциацию `BookGenre`.

```python
# Класс Book
genres: Mapped[list["Genre"]] = relationship(
    back_populates="books",
    secondary="book_genres",
    lazy="noload",
    cascade="all, delete"
)

# Класс Genre
books: Mapped[list["Book"]] = relationship(
    back_populates="genres",
    secondary="book_genres",
    lazy="selectin"
)

# Ассоциация
class BookGenre(Base):
    __tablename__ = "book_genres"
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
```

**Объяснение:**

* В отличии от Django, промежуточную таблицу надо создавать явно.
* Книга может принадлежать нескольким жанрам, и жанр может относиться к нескольким книгам.
* Для реализации создаётся отдельная таблица ассоциации `book_genres`.
* `secondary` в `relationship` указывает на эту таблицу.
* `cascade="all, delete"` может привести к удалению связанных объектов, 
  * поэтому для many-to-many обычно предпочтительно не задавать cascade явно
  * например, указывать `cascade = """`
* `lazy="noload"` или `selectin` — варианты загрузки связанных объектов.

---

## 3. One-to-One (1:1) — один к одному

**Пример:** Книга ↔ Детали книги (`Book` → `BookDetail`)

```python
# В Book
detail: Mapped["BookDetail"] = relationship(
    back_populates="book",
    uselist=False,
    cascade="all, delete-orphan",
    lazy="selectin"
)

# В BookDetail
book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), unique=True, nullable=False)
book: Mapped["Book"] = relationship(
    back_populates="detail",
    lazy="selectin"
)
```

**Объяснение:**

* У каждой книги может быть только одна детальная запись (`BookDetail`), и каждая деталь относится только к одной книге.
* `uselist=False` — ключевой параметр, который делает `relationship` единичным объектом, а не списком.
* `cascade="all, delete-orphan"` — если книга удаляется, её детали удаляются автоматически.

---

## 4. Важные параметры `relationship`

* `back_populates` — двусторонняя связь.
* `lazy` — стратегия загрузки связанных объектов (`select`, `joined`, `selectin`, `noload` и др.).
* `secondary` — таблица ассоциации для Many-to-Many.
* `uselist` — указывает, список это или единичный объект (One-to-One → `False`).
* `cascade` — как изменения/удаления объектов распространяются на связанные объекты.

