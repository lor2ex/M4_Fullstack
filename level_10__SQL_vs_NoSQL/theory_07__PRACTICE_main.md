### `app/main.py`

```python
# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text

from app.db.sql.database import engine
from app.db.mongo.database import client as mongo_client
from app.routers import users, products, orders, payments, reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== STARTUP =====

    # --- SQL check ---
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ SQL database connected")

        # Создаём таблицы после успешного подключения
        from app.db.sql.database import init_models
        await init_models()
        print("✅ SQL tables created")

    except Exception as e:
        print("❌ SQL database connection failed")
        raise e

    # --- Mongo check ---
    try:
        await mongo_client.admin.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print("❌ MongoDB connection failed")
        raise e

    yield

    # ===== SHUTDOWN =====
    await mongo_client.close()
    print("Application shutdown")


app = FastAPI(
    title="Book Store (SQL + MongoDB)",
    lifespan=lifespan,
)

# Routers
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])

```

---

### **app/main.py — разбор по блокам**

#### 1. Импорты БД

* Импортируем `engine` — объект подключения к PostgreSQL через **asyncpg**, который использует пул соединений.

  * Пул позволяет 
    * **повторно использовать соединения**, не создавая новое при каждом запросе.
    * автоматически закрывать ненужные соединения

* Импортируем `mongo_client` для работы с MongoDB.

  * MongoDB не использует пул автоматически, поэтому его соединение нужно закрывать вручную при завершении работы приложения.


---

#### 2. Проверка соединений и создание таблиц SQL

```python
async with engine.connect() as conn:
    await conn.execute(text("SELECT 1"))
print("✅ SQL database connected")

from app.db.sql.database import init_models
await init_models()
print("✅ SQL tables created")
```

* `SELECT 1` — простая проверка доступности PostgreSQL.
* `init_models()` создаёт таблицы (Users, Products, Orders, OrderItems, Payments), если их ещё нет.
* Важно: **подключение через `asyncpg` использует `pool`**, 
  * поэтому один вызов `engine.connect()` берёт соединение из пула.

---

#### 3. Проверка подключения к MongoDB

```python
await mongo_client.admin.command("ping")
print("✅ MongoDB connected")
```

* Отправляем команду `ping` — MongoDB возвращает ответ, если соединение активно.
* MongoDB не создаёт пул соединений автоматически в async-клиенте, поэтому важно иметь открытый клиент.
* В конце приложения мы **закрываем соединение вручную**:

```python
await mongo_client.close()
```

* Это гарантирует, что все ресурсы освобождены, соединение не "висит" и не блокирует завершение приложения.

---

#### 5. Подключение роутеров

```python
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
```
---

