## Подготовка проекта Python + SQLAlchemy + Alembic

### 1. Структура проекта

```
project/
├── docker-compose.yml
├── .env
├── requirements.txt
├── database.py
├── models/
│   ├── __init__.py
│   └── user.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
└── alembic.ini
```

---

### 2. Docker Compose

`docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:17
    container_name: async_postgres
    env_file:
      - .env
    ports:
      - "5435:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Запуск:

```bash
docker compose up -d
```

---

### 3. `.env`

```env
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=mydb
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
```

---

### 4. Зависимости

```bash
pip install sqlalchemy[asyncio] asyncpg python-dotenv alembic

pip freeze > requirements.txt
```


---

### 5. `database.py`

```python
import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass
```

⚠️ **Важно**: Alembic будет использовать **sync-URL**, мы это учтём ниже.

---

### 6. Модель `User`

`models/user.py`

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String

from database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, unique=True)
```

`models/__init__.py`

```python
from .user import User
```

⚠️ Это нужно, чтобы Alembic «увидел» модели.

---

### 7. Инициализация Alembic

```bash
alembic init alembic
```

Будут созданы:

```
alembic/
alembic.ini
```

---

### 8. Настройка `alembic.ini`

⚠️ Alembic работает ТОЛЬКО с sync-engine

Меняем строку подключения:

```ini
sqlalchemy.url = postgresql+psycopg2://myuser:mypassword@localhost:5435/mydb
```

⚠️ **asyncpg здесь НЕ используется**

Поэтому специально для Alembic добавляем `psycopg2-binary`:

```bash
pip install psycopg2-binary

pip freeze > requirements.txt
```


---

### 9. `alembic/env.py` (КЛЮЧЕВОЙ ФАЙЛ)

Файл `alembic/env.py` создаётся автоматически.

Но в него обязательно следует добавить импорты:
```python
from database import Base
from models import *  # noqa
```

И `target_metadata = None` необходимо заменить на:
```python
target_metadata = Base.metadata
```

---

### 10. Создание миграции

```bash
alembic revision --autogenerate -m "create user table"
```

В `alembic/versions/XXXX_create_people_table.py` появится:

```python
def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )


def downgrade():
    op.drop_table('user')
```

---

### 11. Применение миграции

1. Перед применением миграции убедимся, что таблицы пока действительно нет:

```bash
alembic current
```

Пустая база даст такой результат:

```bash
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

2. Как видим, ничего в БД ещё нет:

* Нет таблицы alembic_version
* Ни одна миграция ещё не применялась

3. Применяем миграции:

```bash
alembic upgrade head
```

4. Должна появиться новая строчка:

```bash
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> ce973c8f81fd, create people table
```

Таким образом:
* upgrade выполнился
* Alembic создал таблицу `people` и записал текущую ревизию: ce973c8f81fd

Проверим таблицу непосредственно в контейнере:

```bash
docker exec -it async_postgres sh

psql -U myuser -d mydb

\dt
\d user
SELECT * FROM "user";
```

