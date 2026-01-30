Реализуем всё вышесказанное на практике

### Структура проекта

```
app/
├─ main.py
├─ routers/
│  ├─ users.py
│  └─ items.py
```

---

### 1. `app/routers/users.py`

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Получить всех пользователей
@router.get("/")
async def get_users():
    return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

# Получить пользователя по id
@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id, "name": f"User {user_id}"}
```

---

### 2. `app/routers/items.py`

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/items",
    tags=["Items"]
)

# Получить все предметы
@router.get("/")
async def get_items():
    return [{"id": 1, "name": "Item A"}, {"id": 2, "name": "Item B"}]

# Получить предмет по id
@router.get("/{item_id}")
async def get_item(item_id: int):
    return {"id": item_id, "name": f"Item {item_id}"}
```

---

### 3. `app/main.py`

```python
from fastapi import FastAPI
from app.routers import users, items  # импорт роутеров

app = FastAPI(title="Пример FastAPI с APIRouter")

# Подключение роутеров
app.include_router(users.router)
app.include_router(items.router)
```

---

Теперь при запуске (`uvicorn app.main:app --reload`) будут доступны следующие эндпойнты:

| Метод | URL              | Описание           |
| ----- | ---------------- | ------------------ |
| GET   | /users/          | Все пользователи   |
| GET   | /users/{user_id} | Пользователь по id |
| GET   | /items/          | Все предметы       |
| GET   | /items/{item_id} | Предмет по id      |

