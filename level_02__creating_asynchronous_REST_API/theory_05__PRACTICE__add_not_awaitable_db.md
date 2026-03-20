## НЕ awaitable ("синхронное") подключение Базы Данных

Разумеется, хранить данные в словаре можно только в учебном примере.  
Мало-мальски серьёзные проекты просто обязаны использовать БД.

В этом примере мы подключимся к БД с помощью ORM SQLAlchemy наиболее простым образом:  
не использую все возможности этого пакета по совместимости с asyncio.

Проще говоря, каждое обращение к БД будет блокировать работу проекта   
на это короткое время чтения/записи из/в БД.

---

### 1. Добавление недостающих зависимостей

```bash
pip install sqlalchemy
```

---

### 2. Структура проекта осталась без изменений

```
app/
├── main.py
├── db/
│   ├── models.py        # Pydantic + SQLAlchemy модели
│   ├── repository.py    # CRUD через SQLAlchemy
│   ├── initial_data.py  # начальные данные
│   └── __init__.py
├── routers/
│   ├── books.py
│   └── __init__.py
```

---

### 3. `app/db/models.py` — SQLAlchemy + Pydantic

```python
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# SQLAlchemy модель
class BookORM(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)

# Pydantic модель
class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None

    class Config:
        # orm_mode = True  Устарело. Было в V1
        # ниже - новая реализация orm_mode для V2
        from_attributes = True # позволяет конвертировать из ORM объекта
```

---

### 4. `app/db/repository.py` — простой CRUD через SQLAlchemy

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import BookORM, Book, Base
from .initial_data import initial_books

# SQLite база в файле
DATABASE_URL = "sqlite:///./books.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Создаём таблицы
Base.metadata.create_all(bind=engine)

class BookRepository:
    def __init__(self):
        # загружаем начальные данные
        self._load_initial_data()

    def _load_initial_data(self):
        db: Session = SessionLocal()
        if db.query(BookORM).count() == 0:
            for book in initial_books:
                # db.add(BookORM(**book.dict()))      # v1
                db.add(BookORM(**book.model_dump()))  # v2            
            db.commit()
        db.close()

    def create(self, book: Book) -> Book:
        db: Session = SessionLocal()
        # db_book = BookORM(**book.dict())      # v1
        db_book = BookORM(**book.model_dump())  # v2
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
        db.close()
        # return Book.orm_mode(db_book)         # v1
        return Book.model_validate(db_book)     # v2

    def get_all(self) -> list[Book]:
        db: Session = SessionLocal()
        books = db.query(BookORM).all()
        db.close()
        # return [Book.orm_mode(b) for b in books]      # v1
        return [Book.model_validate(b) for b in books]  # v2

    def get(self, book_id: int) -> Book | None:
        db: Session = SessionLocal()
        book = db.query(BookORM).filter(BookORM.id == book_id).first()
        db.close()
        # return Book.orm_mode(book) if book else None      # v1
        return Book.model_validate(book) if book else None  # v2

    def update(self, book_id: int, new_book: Book) -> Book:
        db: Session = SessionLocal()
        book = db.query(BookORM).filter(BookORM.id == book_id).first()
        if not book:
            db.close()
            raise ValueError("Book not found")
        book.title = new_book.title
        book.author = new_book.author
        book.year = new_book.year
        db.commit()
        db.refresh(book)
        db.close()
        # return Book.orm_mode(book)      # v1
        return Book.model_validate(book)  # v2

    def delete(self, book_id: int):
        db: Session = SessionLocal()
        book = db.query(BookORM).filter(BookORM.id == book_id).first()
        if not book:
            db.close()
            raise ValueError("Book not found")
        db.delete(book)
        db.commit()
        db.close()
```

---

### 5. `app/db/initial_data.py` — начальные данные без изменений


---

### 6. `app/routers/books.py` — роуты без изменений


---

### 7. main.py — и подключение роутов тоже без изменений


---

### Что получилось в итоге

* Вся логика **осталась простой**, как в in-memory варианте.
* Используем **SQLite** через SQLAlchemy.
* Начальные данные автоматически загружаются при старте, если таблица пустая.
* Pydantic модели и роуты **не изменились**.

