## Практические паттерны


В FastAPI с Pydantic есть проверенные практики для организации схем и работы с данными,  
чтобы код был читаемым, безопасным и легко документируемым.

---

### 1. Разделение схем по слоям

Часто создают отдельные модели для запросов и ответов:

```python
from pydantic import BaseModel

# Схема запроса
class UserCreate(BaseModel):
    username: str
    password: str

# Схема ответа
class UserRead(BaseModel):
    username: str
    id: int
```

* **Request** (`UserCreate`) → тело запроса.
* **Response** (`UserRead`) → данные, которые возвращаем клиенту.
* Позволяет исключать чувствительные поля, например `password`.

---

### 2. Использование Pydantic для Depends

Pydantic-модели можно использовать не только для body, но и для валидации параметров в Depends:

```python
from fastapi import Depends

class FilterParams(BaseModel):
    min_price: float = 0
    max_price: float = 1000

@app.get("/items/")
async def list_items(filters: FilterParams = Depends()):
    return filters
```

* Позволяет удобно передавать и валидировать Query-параметры через модель.
* Вложенные и составные фильтры легко документируются в Swagger.

---

### 3. Динамическая генерация схем для OpenAPI

Можно создавать модели на лету с помощью `create_model`:

```python
from pydantic import create_model

DynamicModel = create_model("DynamicModel", name=(str, ...), age=(int, 18))

@app.post("/dynamic/")
async def dynamic_endpoint(data: DynamicModel):
    return data
```

* Полезно, если структура данных заранее неизвестна.
* Swagger UI покажет автоматически сгенерированную схему.

---

### 4. Использование `exclude_unset` и `exclude_none` для PATCH-запросов

При частичном обновлении данных удобно отправлять только изменённые поля:

```python
class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

@app.patch("/items/{item_id}")
async def update_item(item_id: int, item: ItemUpdate):
    return item.model_dump(exclude_unset=True)
```

* Только поля, которые реально переданы → попадают в JSON.
* Удобно для частичных обновлений без перезаписи всех значений.

---

## Итог по практическим паттернам:

* Разделение схем **Request / Response** → безопасность и читаемость.
* Pydantic в Depends → валидация параметров запроса.
* Динамические модели → гибкость и адаптация под OpenAPI.
* `exclude_unset` / `exclude_none` → удобство для PATCH и частичных обновлений.

