## 1. Фикстуры в `test_routes_db.py`

---

### 1.1. `async_client_with_db`

**Задача:**
Асинхронный клиент FastAPI с реальной базой данных (SQLite in-memory). Позволяет интеграционно тестировать эндпоинты, включая репозиторий и SQLAlchemy.

**Реализация:**

* Использует `ASGITransport` и `AsyncClient`.
* Перед тестом подменяет зависимость `get_session` на сессию `db_session`.
* Закрывается после завершения теста.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture
async def async_client_with_db(override_get_db):
    """Асинхронный клиент FastAPI с реальной DB"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

### 1.2. `db_engine`

**Задача:**
Создаёт in-memory SQLite движок для интеграционных тестов.

**Реализация:**

* Асинхронная фикстура с `scope="session"` — создаёт движок один раз на всю сессию тестов.
* Создаёт все таблицы через `Base.metadata.create_all`.

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

### 1.3. `db_session`

**Задача:**
Асинхронная сессия SQLAlchemy для тестов с реальной БД.

**Реализация:**

* Использует `sessionmaker` с `AsyncSession`.
* Перед каждым тестом очищает таблицу `books`.
* Позволяет тестам быть независимыми друг от друга.

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

### 1.4. `override_get_db`

**Задача:**
Подмена зависимости `get_session` для FastAPI на реальную сессию `db_session`.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture
async def override_get_db(db_session):
    async def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()
```

---

### 1.5. `created_book`

**Задача:**
Фикстура-хелпер для создания книги через эндпоинт в реальной БД.
Позволяет использовать один и тот же код создания книги во многих тестах.

**Пример кода фикстуры:**

```python
@pytest_asyncio.fixture
async def created_book(async_client_with_db):
    async def _create(book_obj):
        payload = book_obj.model_dump()
        resp = await async_client_with_db.post("/books/", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        return data["id"], data

    return _create
```

---

## 2. Тесты в `test_routes_db.py`

---

### 2.1. `test_create_book_db`

**Что тестируем:**

* Создание книги через эндпоинт с реальной DB.
* Проверка: статус-код 200 и корректность возвращаемых данных.

**Пример кода теста:**

```python
async def test_create_book_db(async_client_with_db, book_data, created_book):
    book_id, data = await created_book(book_data)
    assert data["id"] == book_id
    assert data["title"] == book_data.title
```

---

### 2.2. `test_get_books_db`

**Что тестируем:**

* Получение всех книг из реальной базы.
* Проверка: список книг не пустой после создания хотя бы одной книги.

**Пример кода теста:**

```python
async def test_get_books_db(async_client_with_db, book_data, created_book):
    await created_book(book_data)
    resp = await async_client_with_db.get("/books/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

---

### 2.3. `test_get_book_db`

**Что тестируем:**

* Получение конкретной книги по ID из реальной базы.
* Проверка совпадения всех полей с созданной книгой.

**Пример кода теста:**

```python
async def test_get_book_db(async_client_with_db, book_data, created_book):
    book_id, created = await created_book(book_data)
    resp = await async_client_with_db.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
```

---

### 2.4. `test_update_book_db`

**Что тестируем:**

* Обновление книги через PUT в реальной базе.
* Проверка: данные книги обновились.

**Пример кода теста:**

```python
async def test_update_book_db(async_client_with_db, book_data, created_book):
    book_id, _ = await created_book(book_data)
    updated = {
        "id": book_id,
        "title": "Updated Book",
        "author": "Jane Doe",
        "year": 2000,
    }
    resp = await async_client_with_db.put(f"/books/{book_id}", json=updated)
    assert resp.status_code == 200
    assert resp.json() == updated
```

---

### 2.5. `test_delete_book_db`

**Что тестируем:**

* Удаление книги через DELETE в реальной базе.
* Проверка: книга больше не существует.

**Пример кода теста:**

```python
async def test_delete_book_db(async_client_with_db, book_data, created_book):
    book_id, _ = await created_book(book_data)
    resp = await async_client_with_db.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    resp = await async_client_with_db.get(f"/books/{book_id}")
    assert resp.status_code == 404
```

---

## Отличия `test_routes.py` и `test_routes_db.py`

| Аспект                      | `test_routes.py`                  | `test_routes_db.py`                  |
| --------------------------- | --------------------------------- | ------------------------------------ |
| Клиент                      | `async_client` с моками           | `async_client_with_db` с реальной DB |
| Проверка данных             | Через моки (не затрагивает DB)    | Через реальную базу                  |
| Скорость тестов             | Быстро, изолировано               | Медленнее, требует поднятой БД       |
| Фикстуры для создания книги | `create_book` (мок POST)          | `created_book` (реальный POST)       |
| Цель                        | Юнит/интеграция эндпоинтов без БД | Интеграция эндпоинтов и репозитория  |


## Тесты 'tests/test_routes_db.py'

```python
import pytest

# ----------------------------------------------------------------------
# CRUD tests с реальной базой
# ----------------------------------------------------------------------
async def test_create_book(created_book, sample_books):
    book = sample_books[0]
    book_id, data = await created_book(book)
    assert data["id"] == book_id
    assert data["title"] == book.title
    assert data["author"] == book.author
    assert data["year"] == book.year


async def test_get_book(created_book, async_client_with_db, sample_books):
    book = sample_books[1]
    book_id, created = await created_book(book)
    resp = await async_client_with_db.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == book_id
    assert data["title"] == created["title"]
    assert data["author"] == created["author"]
    assert data["year"] == created["year"]


async def test_get_books(created_book, async_client_with_db, sample_books):
    for book in sample_books:
        await created_book(book)
    resp = await async_client_with_db.get("/books/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= len(sample_books)


async def test_update_book(created_book, async_client_with_db, sample_books):
    book = sample_books[2]
    book_id, _ = await created_book(book)
    updated_data = {
        "id": book_id,
        "title": "Новая книга",
        "author": "Автор 3 обновлён",
        "year": 2030
    }
    resp = await async_client_with_db.put(f"/books/{book_id}", json=updated_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data == updated_data


async def test_delete_book(created_book, async_client_with_db, sample_books):
    book = sample_books[3]
    book_id, _ = await created_book(book)
    resp = await async_client_with_db.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Book deleted"

    resp = await async_client_with_db.get(f"/books/{book_id}")
    assert resp.status_code == 404
```