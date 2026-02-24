## 1. Фикстуры в `test_routes.py`

В нашем файле используются следующие фикстуры:

---

### 1.1. `async_client`

**Задача:**
Асинхронный клиент FastAPI для тестирования HTTP-запросов к эндпоинтам без реальной базы данных (или с моками).

**Реализация:**

* Использует `httpx.AsyncClient` с `ASGITransport`, чтобы отправлять запросы к FastAPI приложению внутри теста.
* Фикстура асинхронная (`async def`) и автоматически закрывает клиент после использования.

**Пример кода фикстуры:**

```python
@pytest.fixture
async def async_client():
    """Асинхронный клиент FastAPI без базы"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Пример использования в тесте:**

```python
async def test_get_books(async_client):
    resp = await async_client.get("/books/")
    assert resp.status_code == 200
```

---

### 1.2. `book_data`

**Задача:**
Предоставляет тестовую книгу (ORM объект), чтобы использовать её для создания записей через эндпоинты.

**Реализация:**

* Синхронная фикстура (`def`).
* Возвращает объект `Book` с заранее заданными полями (`id`, `title`, `author`, `year`).

**Пример кода фикстуры:**

```python
@pytest.fixture
def book_data():
    """Возвращает объект Book для тестов"""
    return Book(
        id=1,
        title="Test Book",
        author="John Doe",
        year=2026
    )
```

**Пример использования в тесте:**

```python
async def test_create_book(async_client, book_data):
    resp = await async_client.post("/books/", json=book_data.model_dump())
    assert resp.status_code == 200
```

---

### 1.3. `create_book`

**Задача:**
Хелпер/фикстура для удобного создания книги через эндпоинт и получения её `id` и JSON-ответа.
Позволяет не дублировать код создания книги в каждом тесте.

**Реализация:**

* Асинхронная фикстура, возвращает функцию `_create`.
* `_create` принимает объект `book_data`, делает POST-запрос к `/books/`, проверяет статус и возвращает `(id, json)`.

**Пример кода фикстуры:**

```python
@pytest.fixture
def create_book(async_client):
    async def _create(book_data):
        resp = await async_client.post("/books/", json=book_data.model_dump())
        assert resp.status_code == 200
        data = resp.json()
        return data["id"], data
    return _create
```

**Пример использования в тесте:**

```python
async def test_get_book(async_client, book_data, create_book):
    book_id, created = await create_book(book_data)
    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 200
```

---

### 1.4. `mock_repo`

**Задача:**
Фикстура, автоматически подменяющая настоящий `BookRepository` на мок-объект `MagicMock` с полностью контролируемым внутренним состоянием.
Позволяет изолировать тесты от реальной базы данных и проверять логику сервисов/роутов, работая только с in-memory списком книг.

**Что делает:**

* Автоматически применяется ко всем тестам (`autouse=True`).
* Создаёт список `books`, который выступает в роли «фейковой БД».
* Создаёт мок `BookRepository` и переопределяет его методы (`create`, `get_all`, `get`, `update`, `delete`) асинхронными функциями, работающими с этим списком.
* Подменяет конструктор `BookRepository`, чтобы любое его создание внутри приложения возвращало замоканный объект.
* Позволяет тестам проверять работу HTTP-эндпоинтов или сервисов без реального репозитория.

**Реализация (пояснение):**

* Каждый метод репозитория реализован как `async` и назначается через `AsyncMock(side_effect=...)`.
* Список `books` хранит объекты `Book` в процессе теста — имитируя CRUD-операции.
* `yield` в конце позволяет pytest корректно завершить фикстуру.

**Пример кода фикстуры:**

```python
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
```

**Пример использования в тестах:**

Не требует явного подключения — мок активируется автоматически:

```python
async def test_create_and_get(async_client, book_data):
    # Создание книги (репозиторий мокируется автоматически)
    resp = await async_client.post("/books/", json=book_data.model_dump())
    assert resp.status_code == 200

    book_id = resp.json()["id"]

    # Получение книги
    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == book_id
```

---

## 2. Тесты в `test_routes.py`

Тесты можно разделить на **CRUD-тесты**:

---

### 2.1. `test_create_book`

**Что тестируем:**

* Эндпоинт `POST /books/`
* Проверяем: статус-код, корректность возвращаемых данных (`id`, `title`, `author`, `year`)

**Пример кода теста:**

```python
async def test_create_book(async_client, book_data, create_book):
    book_id, data = await create_book(book_data)
    assert data["id"] == book_id
    assert data["title"] == book_data.title
    assert data["author"] == book_data.author
    assert data["year"] == book_data.year
```

---

### 2.2. `test_get_books`

**Что тестируем:**

* Эндпоинт `GET /books/`
* Проверяем: статус-код 200, возвращается список книг

**Пример кода теста:**

```python
async def test_get_books(async_client):
    resp = await async_client.get("/books/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

---

### 2.3. `test_get_book`

**Что тестируем:**

* Эндпоинт `GET /books/{id}`
* Проверяем: корректность данных конкретной книги после создания

**Пример кода теста:**

```python
async def test_get_book(async_client, book_data, create_book):
    book_id, created = await create_book(book_data)
    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == created["title"]
    assert data["author"] == created["author"]
    assert data["year"] == created["year"]
```

---

### 2.4. `test_update_book`

**Что тестируем:**

* Эндпоинт `PUT /books/{id}`
* Проверяем: обновление данных книги, совпадение с отправленным payload

**Пример кода теста:**

```python
async def test_update_book(async_client, book_data, create_book):
    book_id, _ = await create_book(book_data)
    updated = {
        "id": book_id,
        "title": "Updated Book",
        "author": "Jane Doe",
        "year": 2000,
    }
    resp = await async_client.put(f"/books/{book_id}", json=updated)
    assert resp.status_code == 200
    data = resp.json()
    assert data == updated
```

---

### 2.5. `test_delete_book`

**Что тестируем:**

* Эндпоинт `DELETE /books/{id}`
* Проверяем: удаление книги, отсутствие книги после удаления

**Пример кода теста:**

```python
async def test_delete_book(async_client, book_data, create_book):
    book_id, _ = await create_book(book_data)
    resp = await async_client.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Book deleted"

    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 404
```

---

## Выводы

1. **Фикстуры**

   * `async_client` → клиент FastAPI
   * `book_data` → тестовые данные книги
   * `create_book` → хелпер для POST-запроса книги

2. **Тесты**

   * CRUD-тесты используют фикстуры для сокращения повторяющегося кода
   * Асинхронные тесты напрямую проверяют статус-коды и возвращаемые данные
   * Фикстуры позволяют изолировать тесты и использовать мок или реальную DB по выбору


## Фикстуры `tests/conftest.py`

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


```

## Тесты `tests/test_routes.py`

```python
import pytest

async def test_create_book(async_client, book_data, create_book):
    book_id, data = await create_book(book_data)
    assert data["id"] == book_id
    assert data["title"] == book_data.title
    assert data["author"] == book_data.author
    assert data["year"] == book_data.year


async def test_get_books(async_client):
    resp = await async_client.get("/books/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_get_book(async_client, book_data, create_book):
    book_id, created = await create_book(book_data)
    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == created["title"]
    assert data["author"] == created["author"]
    assert data["year"] == created["year"]


async def test_update_book(async_client, book_data, create_book):
    book_id, _ = await create_book(book_data)
    updated = {
        "id": book_id,
        "title": "Updated Book",
        "author": "Jane Doe",
        "year": 2000,
    }
    resp = await async_client.put(f"/books/{book_id}", json=updated)
    assert resp.status_code == 200
    data = resp.json()
    assert data == updated

    
async def test_delete_book(async_client, book_data, create_book):
    book_id, _ = await create_book(book_data)
    resp = await async_client.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Book deleted"

    resp = await async_client.get(f"/books/{book_id}")
    assert resp.status_code == 404

```