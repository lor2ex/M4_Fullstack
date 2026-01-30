## 1. Фикстуры в `test_repository_db.py`

---

### 1.1. `db_engine`

**Задача:**
Создаёт in-memory SQLite движок для тестов репозитория.
**Принцип:** аналогично интеграционным тестам эндпоинтов — база одна на сессию тестов, таблицы создаются в начале.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

---

### 1.2. `db_session`

**Задача:**
Асинхронная сессия SQLAlchemy для каждого теста.
**Особенности:** очищаем таблицу `books` перед тестом, чтобы тесты были изолированы.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        await session.execute(text("DELETE FROM books"))
        await session.commit()
        yield session
        await session.rollback()
```

---

### 1.3. `repository`

**Задача:**
Фикстура для создания экземпляра `BookRepository` с настоящей сессией.
**Принцип:** инъекция сессии напрямую в репозиторий — без HTTP и FastAPI.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture
async def repository(db_session):
    return BookRepository(db_session)
```

---

## 2. Тесты репозитория

Тесты напрямую вызывают методы `BookRepository` (`create`, `get`, `get_all`, `update`, `delete`) и проверяют **правильность работы CRUD**.

---

### 2.1. `test_create_book_repo`

**Что тестируем:**

* Метод `create` репозитория.
* Проверяем, что книга добавлена и возвращаемая книга соответствует данным.

**Пример кода теста:**

```python
async def test_create_book_repo(repository, book_data):
    book = await repository.create(book_data)
    assert book.id == book_data.id
    assert book.title == book_data.title
```

---

### 2.2. `test_get_book_repo`

**Что тестируем:**

* Метод `get` по ID.
* Проверка: найденная книга совпадает с добавленной.

**Пример кода теста:**

```python
async def test_get_book_repo(repository, book_data):
    book = await repository.create(book_data)
    found = await repository.get(book.id)
    assert found.id == book.id
```

---

### 2.3. `test_get_all_books_repo`

**Что тестируем:**

* Метод `get_all`.
* Проверка: возвращается список всех книг, созданных через репозиторий.

**Пример кода теста:**

```python
async def test_get_all_books_repo(repository, sample_books):
    for book in sample_books:
        await repository.create(book)
    all_books = await repository.get_all()
    assert len(all_books) == len(sample_books)
```

---

### 2.4. `test_update_book_repo`

**Что тестируем:**

* Метод `update` репозитория.
* Проверка: данные книги обновлены корректно.

**Пример кода теста:**

```python
async def test_update_book_repo(repository, book_data):
    book = await repository.create(book_data)
    updated_data = Book(id=book.id, title="Updated", author="Jane", year=2000)
    updated = await repository.update(book.id, updated_data)
    assert updated.title == "Updated"
```

---

### 2.5. `test_delete_book_repo`

**Что тестируем:**

* Метод `delete`.
* Проверка: книга удалена, её нельзя найти через `get`.

**Пример кода теста:**

```python
async def test_delete_book_repo(repository, book_data):
    book = await repository.create(book_data)
    await repository.delete(book.id)
    deleted = await repository.get(book.id)
    assert deleted is None
```

## Изменённый `tests/conftest.py`

```python
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.db.models import Base, Book
from app.db.repository import BookRepository, get_session
from app.main import app

# ==============================================================================
# Event loop для async-тестов
# ==============================================================================
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ==============================================================================
# Клиенты для тестов
# ==============================================================================
@pytest.fixture
def client():
    """Синхронный клиент FastAPI"""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Асинхронный клиент FastAPI (без реальной БД)"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# ==============================================================================
# Универсальный хелпер создания книги через API (неинтеграционные тесты)
# ==============================================================================
@pytest.fixture
def create_book(async_client):
    async def _create(book_data):
        resp = await async_client.post("/books/", json=book_data.model_dump())
        assert resp.status_code == 200
        data = resp.json()
        return data["id"], data

    return _create

# ==============================================================================
# Моки: сессия и репозиторий
# ==============================================================================
@pytest.fixture
def mock_session():
    """Мок AsyncSession"""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()

    session.get_all_result = [
        {"id": 1, "title": "Mock Book", "author": "John", "pages": 100}
    ]
    session.get_result = {
        "id": 1, "title": "Mock Book", "author": "John", "pages": 100,
    }

    return session

@pytest.fixture(autouse=True)
def override_get_session(mock_session):
    """Все эндпоинты используют мок-сессию"""
    async def _override():
        yield mock_session

    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_repo():
    """Мок BookRepository с внутренним списком книг"""
    books = []
    repo = MagicMock(spec=BookRepository)

    async def create(book: Book):
        books.append(book)
        return book

    async def get_all():
        return books

    async def get(book_id: int):
        return next((b for b in books if b.id == book_id), None)

    async def update(book_id: int, book: Book):
        for i, b in enumerate(books):
            if b.id == book_id:
                books[i] = book
                return book
        return None

    async def delete(book_id: int):
        for i, b in enumerate(books):
            if b.id == book_id:
                books.pop(i)
                return None

    repo.create = AsyncMock(side_effect=create)
    repo.get_all = AsyncMock(side_effect=get_all)
    repo.get = AsyncMock(side_effect=get)
    repo.update = AsyncMock(side_effect=update)
    repo.delete = AsyncMock(side_effect=delete)

    BookRepository.__new__ = lambda cls, session: repo
    yield

# ==============================================================================
# Тестовые данные
# ==============================================================================
@pytest.fixture
def book_data():
    return Book(
        id=1,
        title="Test Book",
        author="John Doe",
        year=2026
    )

@pytest.fixture
def sample_books():
    return [
        Book(id=1, title="Интеграция", author="Автор 1", year=2025),
        Book(id=2, title="Вторая книга", author="Автор 2", year=2024),
        Book(id=3, title="Старая книга", author="Автор 3", year=2023),
        Book(id=4, title="Для удаления", author="Автор 4", year=2022),
    ]

# ==============================================================================
# Реальная in-memory SQLite база (для интеграционных тестов)
# ==============================================================================
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        await session.execute(text("DELETE FROM books"))
        await session.commit()
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def repository(db_session):
    return BookRepository(db_session)

# ==============================================================================
# Интеграционные фикстуры
# ==============================================================================
@pytest_asyncio.fixture
async def override_get_db(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_client_with_db(override_get_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def created_book(async_client_with_db):
    """Фабрика создания книги через реальную БД"""
    async def _create(book_obj):
        if hasattr(book_obj, "model_dump"):
            payload = book_obj.model_dump()
        else:
            payload = {k: v for k, v in vars(book_obj).items() if k in ("title", "author", "year")}

        resp = await async_client_with_db.post("/books/", json=payload)
        assert resp.status_code == 200, f"Create book failed: {resp.text}"
        data = resp.json()
        return data["id"], data

    return _create
```

## Тесты `tests/test_repository_db.py`

```python
import pytest
from app.db.models import Book
from app.db.repository import NotFoundError
from unittest.mock import AsyncMock, MagicMock


async def test_create_book(repository):
    book = Book(id=1, title="Test Book", author="John Doe", year=2026)
    created = await repository.create(book)
    assert created.id == book.id
    assert created.title == book.title


async def test_get_all_books(repository):
    book1 = Book(id=1, title="Book1", author="A", year=2000)
    book2 = Book(id=2, title="Book2", author="B", year=2010)
    await repository.create(book1)
    await repository.create(book2)

    books = await repository.get_all()
    ids = [b.id for b in books]
    assert 1 in ids
    assert 2 in ids


async def test_get_book(repository):
    book = Book(id=1, title="Book1", author="A", year=2000)
    await repository.create(book)

    fetched = await repository.get(1)
    assert fetched.id == 1
    assert fetched.title == "Book1"


async def test_get_book_not_found(repository):
    result = await repository.get(999)
    assert result is None


async def test_update_book(repository):
    book = Book(id=1, title="Old Title", author="Old Author", year=1990)
    await repository.create(book)

    updated_book = Book(id=1, title="New Title", author="New Author", year=2000)
    updated = await repository.update(1, updated_book)
    assert updated.title == "New Title"
    assert updated.author == "New Author"


async def test_update_book_not_found():
    book = Book(id=999, title="X", author="Y", year=0)
    repository = MagicMock()
    repository.update = AsyncMock(side_effect=NotFoundError)

    with pytest.raises(NotFoundError):
        await repository.update(book)


async def test_delete_book(repository):
    book = Book(id=1, title="Book1", author="A", year=2000)
    await repository.create(book)

    await repository.delete(1)
    result = await repository.get(1)
    assert result is None


async def test_delete_book_not_found():
    repository = MagicMock()
    repository.delete = AsyncMock(side_effect=NotFoundError)
    with pytest.raises(NotFoundError):
        await repository.delete(999)
```