### Установка и настройка окружения

Для начала работы с тестами FastAPI необходимо подготовить окружение.  
Основные инструменты:

* **fastapi** — сам фреймворк для API.
* **uvicorn** — ASGI-сервер для запуска приложения.
* **pytest** — фреймворк для тестирования.
* **httpx** — клиент для тестирования асинхронных эндпоинтов.
* **pytest-asyncio** — плагин для поддержки async-тестов в pytest.

Установка через pip:

```bash
pip install fastapi uvicorn[standard] pytest httpx pytest-asyncio sqlalchemy aiosqlite
```

Обратите внимание на различие между обычными и эвейтэбл тестами:

* Для **обычных эндпойнтов** используем `TestClient` из `fastapi.testclient`.
* Для **эвейтэбл эндпойнтов** — `httpx.AsyncClient` и `pytest-asyncio` для поддержки `async def` в тестах.

После установки неплохо будет проверить, что все пакеты установлены корректно:

```bash
python -m pytest --version
python -c "import fastapi; import httpx; print('OK')"
```

#### Также стоит подготовить минимальную структуру проекта для тестов:

```
project/
├── app
│   ├── __init__.py
│   ├── db
│   │   ├── __init__.py
│   │   ├── initial_data.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── main.py
│   └── routers
│       └── books.py
│       
├── pytest.ini
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_routes.py
│   ├── test_repository_db.py
│   └── test_routes_db.py
```

* `app/` — основное приложение FastAPI.
* `tests/` — папка с тестами.
* `conftest.py` — место для фикстур pytest (например, клиент или база данных).


#### `pytest.ini`

```ini
[pytest]
pythonpath = .
asyncio_mode = auto
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

Обратите внимание на нововведение: установку режима `asyncio_mode = auto`
