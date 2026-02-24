Давайте скорректируем обработку ошибок в роутерах:

Будет удобно обрабатывать все ошибки в одном месте (в middleware), а не вылавливать их по эндпойнтам.

Идея:

1. Репозиторий выбрасывает **кастомные ошибки** (например `RepositoryError`), 
   * которые автоматически конвертируются middleware в HTTP-ответы.
2. Маршруты становятся максимально **чистыми**, без `try/except`.
3. Все маршруты остаются **асинхронными** через `AsyncSession` и DI.

---

### 1. Создадим кастомные исключения

В `app/db/repository.py` добавим:

```python
class RepositoryError(Exception):
    """Базовое исключение для всех ошибок репозитория."""
    pass

class NotFoundError(RepositoryError):
    """Выбрасывается, когда объект не найден."""
    pass

class AlreadyExistsError(RepositoryError):
    """Выбрасывается при попытке создать объект с существующим уникальным идентификатором."""
    pass
```

И заменим в методах репозитория все `ValueError` на эти кастомные исключения.

Пример метода `create`:

```python
async def create(self, book: Book) -> Book:
    result = await self.session.execute(select(BookORM).where(BookORM.id == book.id))
    existing = result.scalar_one_or_none()
    if existing:
        raise AlreadyExistsError(f"Book with id={book.id} already exists")
    db_book = BookORM(**book.dict())
    self.session.add(db_book)
    await self.session.commit()
    await self.session.refresh(db_book)
    return Book.from_orm(db_book)
```

Методы `get`, `update`, `delete` аналогично используют `NotFoundError`, если объект не найден.

---

### 2. Middleware для обработки кастомных исключений

В `main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers.books import router as books_router
from app.db.repository import init_db, RepositoryError, NotFoundError, AlreadyExistsError
import traceback
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при запуске приложения
    await init_db()
    yield

app = FastAPI(title="Books Async DI API", lifespan=lifespan)

# Подключаем роутеры
app.include_router(books_router)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except AlreadyExistsError as ae:
        return JSONResponse(status_code=400, content={"detail": str(ae)})
    except NotFoundError as ne:
        return JSONResponse(status_code=404, content={"detail": str(ne)})
    except RepositoryError as re:
        return JSONResponse(status_code=400, content={"detail": str(re)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
```

---

### 3.Скорректированные маршруты

В `routers/books.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Book
from app.db.repository import BookRepository, get_session

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=Book)
async def create_book(book: Book, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.create(book)


@router.get("/", response_model=list[Book])
async def get_books(session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.get_all()


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: int, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.get(book_id)  # NotFoundError автоматически обработается middleware

@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, book: Book, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.update(book_id, book)


@router.delete("/{book_id}", response_model=dict)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    await repo.delete(book_id)
    return {"message": "Book deleted"}
```

---

### 4. Изменённый `app/db/repository.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from .models import BookORM, Book, Base
from .initial_data import initial_books

class RepositoryError(Exception):
    """Базовое исключение для всех ошибок репозитория."""
    pass

class NotFoundError(RepositoryError):
    """Выбрасывается, когда объект не найден."""
    pass

class AlreadyExistsError(RepositoryError):
    """Выбрасывается при попытке создать объект с существующим уникальным идентификатором."""
    pass


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
            raise NotFoundError(f"Book with id {book_id} not found")
        book.title = new_book.title
        book.author = new_book.author
        book.year = new_book.year
        await self.session.commit()
        await self.session.refresh(book)
        return Book.from_orm(book)

    async def delete(self, book_id: int):
        result = await self.session.execute(select(BookORM).where(BookORM.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            raise NotFoundError(f"Book with id {book_id} not found")
        await self.session.delete(book)
        await self.session.commit()

```

---

### Преимущества этой архитектуры

1. Маршруты чистые и читаемые — нет `try/except`.
2. Все ошибки централизованно обрабатываются middleware.
3. Легко добавлять новые типы ошибок и расширять middleware.
4. Полная поддержка эвейтэбл SQLAlchemy через `AsyncSession` и DI.

