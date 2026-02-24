## Ошибки и обработка исключений

В FastAPI ошибки валидации и кастомные исключения обрабатываются автоматически  
через Pydantic и встроенные механизмы FastAPI. Это позволяет:
* контролировать формат ответа, 
* логировать ошибки 
* и возвращать клиенту понятные сообщения.

---

### 1. Автоматическая генерация 422 Unprocessable Entity

Любая ошибка валидации Pydantic в теле запроса, query или path автоматически приводит к ответу 422:

```python
from fastapi import FastAPI
from pydantic import BaseModel, constr

app = FastAPI()

class Item(BaseModel):
    name: constr(min_length=3)
    price: float

@app.post("/items/")
async def create_item(item: Item):
    return item
```

* Если `name` короче 3 символов → FastAPI возвращает:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "ensure this value has at least 3 characters",
      "type": "value_error.any_str.min_length",
    }
  ]
}
```

---

### 2. Кастомные обработчики RequestValidationError

Можно переопределять стандартное поведение для всех ошибок валидации:

```python
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"errors": exc.errors(), "body": exc.body}
    )
```

* Позволяет логировать ошибки или возвращать свой формат JSON для клиентов.

---

### 3. Использование ValidationError для логирования

Pydantic `ValidationError` можно ловить вручную:

```python
from pydantic import ValidationError

@app.post("/manual-validation/")
async def manual_validation(data: dict):
    try:
        item = Item(**data)
    except ValidationError as e:
        return {"status": "error", "errors": e.errors()}
    return {"status": "ok", "item": item}
```

* Иногда нужно валидировать данные **до передачи в endpoint** или обрабатывать их по-особому.

---

### 4. Ошибки в кастомных валидаторах

Любые исключения, брошенные в `@model_validator` или `root_validator`, автоматически преобразуются в 422:

```python
class UserCreate(BaseModel):
    username: str

    @model_validator(mode="before")
    def check_username(cls, values):
        if values.get("username") == "admin":
            raise ValueError("username cannot be admin")
        return values
```

* Клиент получит понятный JSON с полем `loc` и сообщением об ошибке.

---

## Итог по теме ошибок:

* Любая валидация Pydantic → автоматически 422 Unprocessable Entity.
* Можно кастомизировать формат ошибок через `RequestValidationError`.
* Вручную ловим `ValidationError`, если нужно дополнительное логирование или обработка.
* Ошибки в кастомных валидаторах также корректно превращаются в 422.


