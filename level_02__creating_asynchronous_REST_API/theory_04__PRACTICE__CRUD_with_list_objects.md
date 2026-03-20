## Простой проект с CRUD эндпойнтами без БД

**На всякий случай:**

```bash
pip install fastapi uvicorn[standard]
```

### Структура проекта


```
app/
├── main.py
├── db/
│   ├── models.py       # Pydantic модели
│   ├── repository.py   # CRUD / Repo классы
│   └── __init__.py
├── routers/
│   ├── books.py
│   └── __init__.py
└── __init__.py
```

---

### `db` без реальной БД

#### Почему модель и её методы логично поместить в `db`?

**1. Это отражает назначение**

Папка `db` = всё, что относится к данным:

* модели данных,
* CRUD / repository,
* доступ к данным (пока in-memory, затем DB).

**2. Подготовка перехода к реальной базе**

При желании папка `db` легко расширяется:

```
db/
    models.py          # Pydantic схемы
    repository.py      # In-memory репозиторий
    engine.py          # подключение БД
    sqlalchemy_models.py   # если нужно
```

**3. Разделение слоёв (чистая архитектура)**

* `db` → данные
* `routers` → API
* `main` → сборка приложения

---

#### `app/db/models.py` — модели Pydantic

```python
from pydantic import BaseModel, Field

class Book(BaseModel):
    id: int = Field(..., example=1)
    title: str
    author: str
    year: int | None = None
```

---

#### `app/db/repository.py — CRUD / Repository

```python
from .models import Book
from .initial_data import initial_books

class BookRepository:
    def __init__(self):
        self._books: list[Book] = []
        self._load_initial_data()

    def _load_initial_data(self):
        """
        Автоматическая загрузка данных при старте проекта
        """
        self._books.extend(initial_books)

    def create(self, book: Book) -> Book:
        if any(b.id == book.id for b in self._books):
            raise ValueError("Book with this ID already exists")
        self._books.append(book)
        return book

    def get_all(self) -> list[Book]:
        return self._books

    def get(self, book_id: int) -> Book | None:
        return next((b for b in self._books if b.id == book_id), None)

    def update(self, book_id: int, new_book: Book) -> Book:
        for i, b in enumerate(self._books):
            if b.id == book_id:
                self._books[i] = new_book
                return new_book
        raise ValueError("Book not found")

    def delete(self, book_id: int) -> None:
        for i, b in enumerate(self._books):
            if b.id == book_id:
                del self._books[i]
                return
        raise ValueError("Book not found")
```

---

#### `app/db/initial_data.py` — начальные данные на "первое время"

```python
from .models import Book

initial_books = [
    Book(id=1, title="Мастер и Маргарита", author="Михаил Булгаков", year=1967),
    Book(id=2, title="Преступление и наказание", author="Фёдор Достоевский", year=1866),
    Book(id=3, title="Три товарища", author="Эрих Мария Ремарк", year=1936),
]

```


---

#### `app/routers/books.py` 

```python
from fastapi import APIRouter, HTTPException
from app.db.models import Book
from app.db.repository import BookRepository

router = APIRouter(prefix="/books", tags=["books"])
repo = BookRepository()

@router.post("/", response_model=Book)
def create_book(book: Book):
    try:
        return repo.create(book)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/", response_model=list[Book])
def get_books():
    return repo.get_all()

@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int):
    book = repo.get(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book

@router.put("/{book_id}", response_model=Book)
def update_book(book_id: int, book: Book):
    try:
        return repo.update(book_id, book)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.delete("/{book_id}", response_model=dict)
def delete_book(book_id: int):
    try:
        repo.delete(book_id)
        return {"message": "Book deleted"}
    except ValueError as e:
        raise HTTPException(404, str(e))
```

---

## `app/main.py` — подключение маршрутов

```python
from fastapi import FastAPI
from app.routers.books import router as books_router

app = FastAPI(title="Books API")

app.include_router(books_router)
```

---

### Запуск проекта и быстрое "ручное" тестирование

```bash
uvicorn app.main:app --reload
```

#### 1. Эндпойнты уже есть, осталось выполнить запросы

Наш `routers/books.py` содержит все стандартные CRUD:

| Метод    | URL                | Действие                  |
| -------- | ------------------ | ------------------------- |
| `GET`    | `/books/`          | Получить список всех книг |
| `POST`   | `/books/`          | Создать новую книгу       |
| `GET`    | `/books/{book_id}` | Получить книгу по ID      |
| `PUT`    | `/books/{book_id}` | Обновить книгу            |
| `DELETE` | `/books/{book_id}` | Удалить книгу             |

---

#### 2. Можно проверить через Swagger

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  
Здесь можно прямо из браузера проверять GET, POST, PUT, DELETE.



---

#### 3. А можно и через curl

**1. Получить все книги**

```bash
curl http://127.0.0.1:8000/books/
```

**Ответ:**

```json
[
  {"id":1,"title":"Мастер и Маргарита","author":"Михаил Булгаков","year":1967},
  {"id":2,"title":"Преступление и наказание","author":"Фёдор Достоевский","year":1866},
  {"id":3,"title":"Три товарища","author":"Эрих Мария Ремарк","year":1936}
]
```

---

**2. Получить книгу по ID**

```bash
curl http://127.0.0.1:8000/books/2
```

**Ответ:**

```json
{"id":2,"title":"Преступление и наказание","author":"Фёдор Достоевский","year":1866}
```

---

**3. Создать новую книгу**

```bash
curl -X POST http://127.0.0.1:8000/books/ -H "Content-Type: application/json" -d '{"id":4,"title":"1984","author":"Джордж Оруэлл","year":1949}'
```

---

**4. Обновить книгу**

```bash
curl -X PUT http://127.0.0.1:8000/books/4 -H "Content-Type: application/json" -d '{"id":4,"title":"1984","author":"George Orwell","year":1949}'
```

---

**5. Удалить книгу**

```bash
curl -X DELETE http://127.0.0.1:8000/books/4
```

---

### Итог

* **Начальные данные** загружаются автоматически через `BookRepository`.
* **Все CRUD эндпоинты работают**.
* Можно проверять через браузер или curl.

