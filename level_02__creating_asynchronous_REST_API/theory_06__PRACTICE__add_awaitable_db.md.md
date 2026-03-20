## Awaitable ("Асинхронное") подключение Базы Данных

Здесь реализован async вариант **Dependency Injection** FastAPI для сессий. Это позволит:

* не создавать новую сессию в каждом методе репозитория,
* автоматически закрывать сессии после запроса,
* облегчить будущее тестирование.

---

### 0. Добавляем пакет `aiosqlite`

```bash
pip install aiosqlite
```

---

### 1. `app/db/repository.py` — с Dependency Injection

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from .models import BookORM, Book, Base
from .initial_data import initial_books
from fastapi import Depends

DATABASE_URL = "sqlite+aiosqlite:///./books_di.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency для FastAPI
# Теперь сессия будет передаваться в эндпойнт и завершаться при выходе из него
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Инициализация БД и начальные данные
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BookORM))
        books = result.scalars().all()
        if not books:
            for book in initial_books:
                session.add(BookORM(**book.model_dump()))
            await session.commit()

class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, book: Book) -> Book:
        db_book = BookORM(**book.model_dump())
        self.session.add(db_book)
        await self.session.commit()
        await self.session.refresh(db_book)
        return Book.model_validate(db_book)

    async def get_all(self) -> list[Book]:
        result = await self.session.execute(select(BookORM))
        books = result.scalars().all()
        return [Book.model_validate(b) for b in books]

    async def get(self, book_id: int) -> Book | None:
        result = await self.session.execute(select(BookORM).where(BookORM.id == book_id))
        book = result.scalar_one_or_none()
        return Book.model_validate(book) if book else None

    async def update(self, book_id: int, new_book: Book) -> Book:
        result = await self.session.execute(select(BookORM).where(BookORM.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise ValueError("Book not found")
        book.title = new_book.title
        book.author = new_book.author
        book.year = new_book.year
        await self.session.commit()
        await self.session.refresh(book)
        return Book.model_validate(book)

    async def delete(self, book_id: int):
        result = await self.session.execute(select(BookORM).where(BookORM.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise ValueError("Book not found")
        await self.session.delete(book)
        await self.session.commit()
```

---

### 2. `app/routers/books.py` — использование DI

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Book
from app.db.repository import BookRepository, get_session

router = APIRouter(prefix="/books", tags=["books"])

# Каждый маршрут получает AsyncSession через Depends
@router.post("/", response_model=Book)
async def create_book(book: Book, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    try:
        return await repo.create(book)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/", response_model=list[Book])
async def get_books(session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.get_all()

@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: int, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    book = await repo.get(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book

@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, book: Book, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    try:
        return await repo.update(book_id, book)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.delete("/{book_id}", response_model=dict)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    try:
        await repo.delete(book_id)
        return {"message": "Book deleted"}
    except ValueError as e:
        raise HTTPException(404, str(e))
```

---

### 3. `app/main.py` — инициализация базы при старте

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers.books import router as books_router
from app.db.repository import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при запуске приложения
    await init_db()
    yield

app = FastAPI(title="Books Async DI API", lifespan=lifespan)

# Подключаем роутеры
app.include_router(books_router)

```

---

## Преимущества такого подхода

1. **Сессии создаются автоматически на каждый запрос** через FastAPI `Depends`.
2. **Репозиторий не заботится о создании сессии** — только о логике CRUD.
3. **Лёгко тестировать**: можно передать мок-сессию.
4. **Асинхронная работа**: FastAPI не блокируется при запросах к базе.
5. **Начальные данные** загружаются один раз при старте приложения.

