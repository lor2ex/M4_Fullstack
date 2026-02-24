## 1. Возврат Python-типов

FastAPI автоматически конвертирует Python-тип в JSON.

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/nums/")
def get_numbers():
    return [1, 2, 3]  # FastAPI отдаст JSON: [1,2,3]

@app.get("/dict/")
def get_dict():
    return {"name": "Alice", "age": 30}  # JSON: {"name":"Alice","age":30}
```

**Особенности**:

* Не требуется отдельная Pydantic-модель
* FastAPI автоматически ставит `application/json`

**Минус**

Если вернуть смешанный список (числа / строки) ошибки не будет.
```python
@app.get("/nums/")
def get_numbers():
    return [1, "two", 3]
```
---

## 2. Использование Pydantic-моделей (рекомендуемый способ)

Позволяет структурировать и валидировать ответ.

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.get(
    "/nums/", 
    response_model=list[Item], 
    response_model_exclude_unset=False
)
def list_items():
    """Возвращает список товаров"""
    return [
        {"name": "Apple", "price": 1.2, "is_offer": True}, 
        {"name": "Banana", "price": 0.8, "is_offer": None}
    ]
```

**Особенности**:

* Автоматическая валидация и сериализация
* Работает со списками и словарями
* Можно скрывать поля через `response_model_exclude`
* Можно скрывать неустановленные поля `response_model_exclude_unset=True`

| Поле       | Передано явно | `exclude_unset=True` | Результат в JSON      |
| ---------- | ------------- | -------------------- | --------------------- |
| `is_offer` | Не передано   | True                 | **не будет в ответе** |
| `is_offer` | Не передано   | False                | null                  |
| `is_offer` | Передано None | True                 | null                  |
| `is_offer` | Передано None | False                | null                  |


---

## 3. Возврат кастомного Response

Можно полностью контролировать ответ, включая тело, заголовки и статус.

```python
from fastapi import Response
from fastapi.responses import JSONResponse, PlainTextResponse

@app.get("/custom/")
def custom_response():
    return JSONResponse(content={"message": "Hello"}, status_code=201)

@app.get("/text/")
def text_response():
    return PlainTextResponse("Just text", status_code=200)
```

**Особенности**:

* Можно использовать `HTMLResponse`, `FileResponse`, `StreamingResponse`
* Полный контроль над типом контента

