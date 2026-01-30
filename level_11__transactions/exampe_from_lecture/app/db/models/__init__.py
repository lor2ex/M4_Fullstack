from .person import Person, PersonCreate, PersonRead  # эти модели уже есть

from .books import (                                  # добавляем новые модели
    Author, Genre, Book, BookDetail, BookGenre, book_to_read

)

# __all__ погоды не делает (достаточно одних импортов), но читабельность улучшает
__all__ = [
    "Person", "PersonCreate", "PersonRead",
    "Author", "Genre", "Book", "BookDetail", "BookGenre", "book_to_read"
]