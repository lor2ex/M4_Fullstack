### Установка пакетов

```bash
pip install fastapi uvicorn[standard] sqlalchemy asyncpg motor python-dotenv

pip freeze > requirements.txt
```

**Назначение:**

| Пакет               | Для чего нужен                          |
| ------------------- |-----------------------------------------|
| `fastapi`           | сам фреймворк                           |
| `uvicorn[standard]` | ASGI сервер для запуска приложения      |
| `sqlalchemy`        | ORM для работы с PostgreSQL             |
| `asyncpg`           | async драйвер PostgreSQL                |
| `motor`             | async драйвер MongoDB                   |
| `python-dotenv`     | загрузка переменных окружения из `.env` |


---

### Автоматическое создание структуры проекта

**Схема структура проекта, и скрипт для её автоматического создания** в модуле `create_structure.py`:

```python
from pathlib import Path

SPACES = 3  # Число пробелов на 1 уровень

tree = """
├─ app/
│  ├─ db/
│  │  ├─ __init__.py
│  │  ├─ sql/
│  │  │  ├─ __init__.py
│  │  │  ├─ models.py
│  │  │  ├─ database.py 
│  │  │  └─ crud.py
│  │  └─ mongo/
│  │     ├─ __init__.py
│  │     ├─ models.py
│  │     ├─ database.py
│  │     └─ crud.py
│  ├─ routers/
│  │  ├─ __init__.py
│  │  ├─ users.py
│  │  ├─ products.py
│  │  ├─ orders.py
│  │  ├─ payments.py
│  │  └─ reviews.py
│  └─ main.py
├─ .env
└─ docker-compose.yml
""".strip()


def create_structure(tree_text: str, root_dir: str = "."):
    root = Path(root_dir).resolve()
    stack = [root]

    for line in tree_text.splitlines():
        if not line.strip():
            continue

        # Считаем уровень вложенности по отступам (4 пробела = 1 уровень)
        stripped = line.lstrip(" │├─└")
        level = (len(line) - len(stripped)) // SPACES

        # Убираем префиксы веток
        name = stripped.strip(" ─└├│")

        if not name:
            continue

        # Возвращаемся на нужный уровень в стеке
        while len(stack) > level:
            stack.pop()

        current = stack[-1]
        path = current / name

        # Папка или файл?
        if name.endswith('/'):
            name = name.rstrip('/')
            path = current / name
            path.mkdir(parents=True, exist_ok=True)
            stack.append(path)
        else:
            # Файл
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.touch(exist_ok=True)
            symbol = "✓" if existed else "✓"

    print("\nСтруктура создана/проверена")


if __name__ == "__main__":
    print("Создание структуры проекта...\n")
    create_structure(tree)
```

---

#### `.env` 

```env
# SQL (PostgreSQL)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=bookstore
SQL_DB_HOST=localhost
SQL_DB_PORT=5433

# MongoDB
MONGO_USER=mongo
MONGO_PASSWORD=mongo
MONGO_DB_NAME=bookstore
MONGO_HOST=localhost
MONGO_PORT=27018
```

> Все подключения к SQL и MongoDB берут параметры из `.env`.

---

#### `docker-compose.yml`

```yaml
services:
  sql_db:
    image: postgres:17
    container_name: sql_db
    restart: always
    env_file:
      - .env
    ports:
      - "5433:5432"
    volumes:
      - sql_data:/var/lib/postgresql/data

  mongo_db:
    image: mongo:7
    container_name: mongo_db
    restart: always
    env_file:
      - .env
    ports:
      - "27018:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  sql_data:
  mongo_data:
```

> Контейнеры используют параметры из `.env`, а данные сохраняются через volumes.
