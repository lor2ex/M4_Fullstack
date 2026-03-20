from fastapi import APIRouter, HTTPException
from typing import List
from app.db.models.books import BookCreate, BookRead, book_to_read
from app.db.repository.books import BookRepository

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/", response_model=List[BookRead])
async def read_books():
    return await BookRepository.list_books()

@router.post("/books/", response_model=BookRead)
async def add_book(data: BookCreate):
    book = await BookRepository.create_book(data)
    return book_to_read(book)

@router.delete("/{book_id}")
async def delete_book(book_id: int):
    ok = await BookRepository.delete_book(book_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book was deleted"}
