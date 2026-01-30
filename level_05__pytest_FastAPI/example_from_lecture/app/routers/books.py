from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Book
from app.db.repository import BookRepository, get_session, NotFoundError

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
    book = await repo.get(book_id)
    if not book:
        raise NotFoundError(f"Book with id={book_id} not found")
    return book

@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: int, book: Book, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    return await repo.update(book_id, book)


@router.delete("/{book_id}", response_model=dict)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)):
    repo = BookRepository(session)
    await repo.delete(book_id)
    return {"message": "Book deleted"}
