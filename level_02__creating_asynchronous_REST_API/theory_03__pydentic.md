## Корректное создание объектов с помощью Pydantic

Удобно вспомнить для валидации и сериализации/десериализации объектов

| **Элемент Pydantic**                                                              | **Назначение / описание**                                       | **Пример**                                                                                                  | **Использование в FastAPI**                        |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `BaseModel`                                                                       | Базовый класс для всех моделей                                  | <code>class User(BaseModel):<br>    id: int;<br>    name: str</code>                                        | Используется для request body и response model     |
| `Field`                                                                           | Настройка полей: значения по умолчанию, ограничения, метаданные | <code>name: str = Field(..., min_length=3, max_length=50)</code>                                            | Автоматическая валидация входных данных в запросах |
| Стандартные Python-типы полей <br>(`int`, `str`, `float`, `bool`, `List`, `Dict`) | Определяют типы данных                                          | <code>tags: List[str] = []</code>                                                                           | FastAPI автоматически проверяет типы данных        |
| `Optional`                                                                        | Поле может быть `None` / необязательное                         | <code>age: Optional[int] = None</code>                                                                      | Request body может быть неполным                   |
| Специальные типы (`EmailStr`, `HttpUrl`, `IPvAnyAddress`)                         | Валидация форматов                                              | <code>email: EmailStr</code>                                                                                | Проверка email, URL, IP в запросах                 |
| Ограниченные типы (`conint`, `confloat`, `constr`)                                | Задают диапазон или длину                                       | <code>score: conint(ge=0, le=100)</code>                                                                    | Автоматическая валидация значений                  |
| `@validator`                                                                      | Кастомная валидация полей                                       | <code>@validator('age')<br>def positive(cls, v):<br>    if v < 0: raise ValueError()<br>    return v</code> | Можно проверять бизнес-логику входных данных       |
| `Config`                                                                          | Настройки модели (`orm_mode`, `anystr_strip_whitespace`)        | <code>class Config:<br>    orm_mode = True</code>                                                           | Важно для работы с ORM и корректной сериализации   |
| Вложенные модели                                                                  | Модели внутри моделей                                           | <code>class Address(BaseModel):<br>    street: str;<br>    city: str</code>                                 | FastAPI автоматически парсит вложенный JSON        |
| Response model                                                                    | Указывается в endpoint для ответа                               | <code>@app.post("/users/", response_model=User)</code>                                                      | Автоматическая сериализация и документация OpenAPI |




Пример FastAPI с использованием всех этих элементов:

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr, conint
from typing import List, Optional

app = FastAPI()

class Address(BaseModel):
    street: str
    city: str

class User(BaseModel):
    id: int                                 # Обязательное поле (нет значения по умолчанию), целое число
    name: str = Field(..., min_length=3)    # Обязательное поле (есть многоточие), строка длиной не менее 3-х символов
    email: EmailStr                         # Обязательное поле (нет значения по умолчанию), стока в формате email
    age: int | None = Field(None, ge=0, le=120)  # Необязательное поле (есть значение по умолчанию), целое от 0 до 120 или None
    tags: list[str] = []                    # Необязательное поле (есть значение по умолчанию), список строк
    address: Address                        # Обязательное поле (нет значения по умолчанию), объект Address

    class Config:
        orm_mode = True

@app.post("/users/", response_model=User)
async def create_user(user: User):
    return user
```

Здесь мы видим:

* Обязательные и необязательные поля (`name`, `age`)
* Валидацию типов (`email`, `tags`)
* Ограничения (`age`)
* Вложенные объекты (`address`)
* Использование в FastAPI (`request body` и `response_model`)


## Пример сериализации / десериализации

### 1. Десериализация (парсинг входных данных)

Pydantic-модели умеют принимать «сырые» данные (dict, JSON-строки, объекты других типов)   
и преобразовывать их в Python-объекты с правильными типами.

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

u = User.model_validate({"id": "1", "name": "Alice"})
print(u.id)        # 1 (int)
print(type(u.id))  # <class 'int'>
```

Pydantic не только валидирует данные, но и преобразует их в нужные типы 

---

### 2. Сериализация (преобразование модели в dict / JSON)

Pydantic может преобразовать модель обратно в dict или JSON.

```python
u.model_dump()         # {'id': 1, 'name': 'Alice'}
u.model_dump_json()    # '{"id":1,"name":"Alice"}'
```

Также можно управлять сериализацией — исключать поля, переименовывать, скрывать приватные и т. д.

---

### 3. Pydentic-методы сериализации / десериализации

* `model_validate()` — десериализация
* `model_validate_json()` — десериализация JSON
* `model_dump()` — сериализация в dict
* `model_dump_json()` — сериализация в JSON
