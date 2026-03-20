В FastAPI нет файла `settings.py`, привычного нам по Django.

Но есть несколько вариантов и способов задать настройки проекта.

# 1. Конфигурация настроек проекта (Pydantic Settings)

**Файл: `app/config.py`**

Используется для:

* чтения `.env`
* хранения настроек БД
* включения/выключения Debug
* конфигов приложения

Пример:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My API"
    debug: bool = False
    database_url: str

    class Config:
        env_file = ".env"

settings = Settings()
```

Использование:

```python
from app.config import settings
print(settings.database_url)
```

**Это ключевой файл любого FastAPI-проекта.**

---

# 2. Конфигурация FastAPI-приложения

**Файл: `app/main.py`**

Создаёт приложение, подгружает настройки, регистрирует роуты.

```python
# app/main.py
from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)
```

В этом файле настраиваются:

* `FastAPI(title=..., debug=...)`
* подключение CORS (если нужно)
* подключение маршрутов

Это *центральная точка входа*.

---

# 3. Конфигурация базы данных

**Файл: `app/db.py`**

Минимальная и самая распространённая настройка:

```python
# app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
```

Эта конфигурация встречается ВЕЗДЕ, если используется SQLAlchemy.

---

Есть и другие способы, о которых мы познакомимся позже.