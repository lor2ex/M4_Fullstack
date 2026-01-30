# Схемы запросов и ответов

## 1. Request Body

В FastAPI **любые данные из тела запроса** передаются через модели Pydantic (`BaseModel`).
Используем POST/PUT/PATCH для создания или изменения ресурсов.

### 1.1. Пример: простая модель

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True  # значение по умолчанию

@app.post("/items/")
async def create_item(item: Item):
    return {"message": "Item created", "item": item}
```

* FastAPI автоматически проверяет типы (`str`, `float`, `bool`).
* Если данные невалидные → 422 Unprocessable Entity.
* `item` внутри функции уже объект Pydantic, доступ к полям через `item.name`, `item.price`.

---

### 1.2. Вложенные модели

Иногда объект содержит вложенные структуры (например, адрес пользователя).

```python
from typing import List

class Address(BaseModel):
    city: str
    country: str

class UserCreate(BaseModel):
    username: str
    email: str
    addresses: List[Address]

@app.post("/users/")
async def create_user(user: UserCreate):
    return {"user": user}
```

* В `addresses` можно передавать список объектов `Address`.
* FastAPI и Pydantic автоматически валидируют вложенные данные.
* Swagger UI сразу показывает структуру вложенных объектов.

---

### 1.3. Валидация списков объектов

```python
class Item(BaseModel):
    name: str
    price: float

class Order(BaseModel):
    items: List[Item]

@app.post("/orders/")
async def create_order(order: Order):
    return {"order": order}
```

* Список объектов проверяется полностью.
* Если один элемент невалиден → весь запрос отклоняется.

---

## 2. Response Model

FastAPI позволяет **явно указывать модель ответа** через `response_model`.  
Это важно для документации, фильтрации полей и контроля формата ответа.

```python
from pydantic import EmailStr

class UserRead(BaseModel):
    username: str
    email: EmailStr

@app.get("/users/{user_id}", response_model=UserRead)
async def read_user(user_id: int):
    user = {"username": "alice", "email": "alice@example.com", "password": "secret"}
    return user
```

* Поле `password` автоматически **исключается**.
* Swagger UI показывает только `username` и `email`.

---

### 2.1. Исключение полей и unset

```python
@app.get("/users/{user_id}", response_model=UserRead, response_model_exclude={"email"})
async def read_user_exclude(user_id: int):
    return {"username": "alice", "email": "alice@example.com"}
```

* Можно исключать поля на лету.
* `_exclude_unset=True` полезно для PATCH-запросов: возвращаются только установленные поля.

---

### 2.2. Переименование полей через alias

```python
class UserRead(BaseModel):
    user_name: str = Field(..., alias="username")

@app.get("/users/{user_id}", response_model=UserRead, response_model_by_alias=True)
async def read_user_alias(user_id: int):
    return {"username": "alice"}
```

* В JSON будет поле `username` вместо `user_name`.
* Позволяет разделять внутренние имена полей и внешний API.

---

## 3. Примеры запросов и документация

FastAPI позволяет добавлять **пример запроса** прямо в модель:

```python
class Item(BaseModel):
    name: str = Field(..., example="Laptop")
    price: float = Field(..., example=1999.99)

@app.post("/items/")
async def create_item(item: Item):
    return item
```

* Swagger UI автоматически показывает пример запроса.
* Можно также использовать `examples` для нескольких примеров.

---

### Автогенерация документации

* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc: `http://127.0.0.1:8000/redoc`
* Все `BaseModel` автоматически конвертируются в JSON Schema для OpenAPI.
* Вложенные модели, alias, примеры — все отображается красиво.

---

## Итог по теме Request/Response в FastAPI:

* `BaseModel` для запроса → автоматическая валидация.
* Вложенные модели и списки → удобная структура JSON.
* `response_model` → фильтрация, документация, безопасность.
* Alias и exclude → гибкая сериализация.
* Примеры и OpenAPI → автогенерация Swagger/ReDoc без лишнего кода.

