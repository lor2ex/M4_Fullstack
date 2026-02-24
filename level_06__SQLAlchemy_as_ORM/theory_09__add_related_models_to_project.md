В нашем последнем Django-проекта в Django ORM была реляционная БД Books:

`myapp/models`

```python
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=200)
    year_published = models.IntegerField()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({self.author})"


class BookDetail(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name='detail')
    summary = models.TextField()
    page_count = models.IntegerField()

    def __str__(self):
        return f"Details for {self.book.title}"


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    books = models.ManyToManyField(Book, related_name='genres')

    def __str__(self):
        return self.name
```

Попробуем реализовать ту же схему на SQLAlchemy, и организовать CRUD доступ с помощью FastAPI.

Ниже — пример данных для заполнения БД:

`books.json`

```json
{
  "authors": [
    {"id": 1, "name": "Leo Tolstoy"},
    {"id": 2, "name": "Fyodor Dostoevsky"},
    {"id": 3, "name": "Jane Austen"},
    {"id": 4, "name": "Mark Twain"},
    {"id": 5, "name": "George Orwell"}
  ],
  "genres": [
    {"id": 1, "name": "Classic"},
    {"id": 2, "name": "Fiction"},
    {"id": 3, "name": "Satire"},
    {"id": 4, "name": "Romance"},
    {"id": 5, "name": "Dystopian"}
  ],
  "books": [
    {"id": 1, "title": "War and Peace", "author_id": 1, "year_published": 1869, "is_deleted": false, "genre_ids": [1, 2]},
    {"id": 2, "title": "Anna Karenina", "author_id": 1, "year_published": 1877, "is_deleted": false, "genre_ids": [1, 4]},
    {"id": 3, "title": "Crime and Punishment", "author_id": 2, "year_published": 1866, "is_deleted": false, "genre_ids": [1, 2]},
    {"id": 4, "title": "The Idiot", "author_id": 2, "year_published": 1869, "is_deleted": false, "genre_ids": [1, 2]},
    {"id": 5, "title": "Pride and Prejudice", "author_id": 3, "year_published": 1813, "is_deleted": false, "genre_ids": [1, 4]},
    {"id": 6, "title": "Emma", "author_id": 3, "year_published": 1815, "is_deleted": false, "genre_ids": [1, 4]},
    {"id": 7, "title": "Adventures of Huckleberry Finn", "author_id": 4, "year_published": 1884, "is_deleted": false, "genre_ids": [2, 3]},
    {"id": 8, "title": "The Adventures of Tom Sawyer", "author_id": 4, "year_published": 1876, "is_deleted": false, "genre_ids": [2, 3]},
    {"id": 9, "title": "1984", "author_id": 5, "year_published": 1949, "is_deleted": false, "genre_ids": [2, 5]},
    {"id": 10, "title": "Animal Farm", "author_id": 5, "year_published": 1945, "is_deleted": false, "genre_ids": [2, 3, 5]}
  ],
  "book_details": [
    {"book_id": 1, "summary": "Epic novel about Russian society during Napoleonic wars.", "page_count": 1225},
    {"book_id": 2, "summary": "Tragic love story set in Russian aristocracy.", "page_count": 864},
    {"book_id": 3, "summary": "Psychological novel exploring guilt and redemption.", "page_count": 671},
    {"book_id": 4, "summary": "A story of innocence and moral dilemmas in Russia.", "page_count": 656},
    {"book_id": 5, "summary": "Romantic novel about manners and society in England.", "page_count": 432},
    {"book_id": 6, "summary": "Story of young woman navigating love and social norms.", "page_count": 474},
    {"book_id": 7, "summary": "Adventures of a boy along the Mississippi River.", "page_count": 366},
    {"book_id": 8, "summary": "Youthful adventures and mischief in a small town.", "page_count": 274},
    {"book_id": 9, "summary": "Dystopian novel about a totalitarian regime.", "page_count": 328},
    {"book_id": 10, "summary": "Allegorical novella satirizing political systems.", "page_count": 112}
  ]
}
```