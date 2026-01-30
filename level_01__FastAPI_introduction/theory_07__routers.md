Вы спрашиваете про **группировку эндпойнтов в FastAPI**. В FastAPI это делается с помощью **`APIRouter`**. 
Давайте разберём всё подробно:

---

## Роутер в FastAPI


### 1. Что такое роутер в FastAPI?

**Роутер** в FastAPI — это объект для группировки эндпойнтов.

```python
from fastapi import APIRouter
```

* **Класс:** `APIRouter`
* Используется для создания логических групп эндпойнтов, которые подключаются к основному приложению FastAP 
  * с помощью метода `app.include_router(router)`

---

### 2 Когда применяется?

`APIRouter` применяют, когда нужно:

* Разделить API на **логические модули** (например: `users`, `items`, `auth`).
* Избежать огромного `main.py` с десятками эндпойнтов.
* Добавить **общие зависимости**, **теги**, **префиксы URL** и **middleware** к группе эндпойнтов.
* Повысить **читаемость и масштабируемость** проекта.

Пример логического разделения:

```
app/
├─ main.py
├─ routers/
│  ├─ users.py
│  ├─ items.py
```

---

### 3 Где находятся в приложении?

* Обычно в отдельной папке `routers` или `api`, внутри которой по файлам лежат группы эндпойнтов.
* Каждая группа эндпойнтов создается через `APIRouter`.

Пример структуры:

```text
app/
├─ main.py
├─ routers/
│  ├─ users.py
│  └─ items.py
```

---

### 4 Как импортируется?

1. В файле с роутером создаём `APIRouter`:

```python
# routers/users.py
from fastapi import APIRouter

router = APIRouter(
    prefix="/users",  # префикс для всех эндпойнтов
    tags=["Users"],   # теги для документации
)

@router.get("/")
async def list_users():
    return [{"id": 1, "name": "Alice"}]
```

2. В основном приложении подключаем:

```python
# main.py
from fastapi import FastAPI
from routers import users  # импортируем файл users.py

app = FastAPI()

app.include_router(users.router)  # подключаем роутер
```

Теперь все эндпойнты из `users.py` будут доступны под `/users/...`.
