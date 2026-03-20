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
