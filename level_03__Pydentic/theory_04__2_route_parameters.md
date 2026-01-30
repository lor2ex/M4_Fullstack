## Параметры маршрутов (Path, Query, Header, Cookie)

В FastAPI все параметры, которые приходят через URL или заголовки,  
могут быть типизированы и валидированы через Pydantic.

### 1. Path-параметры

Path-параметры передаются в URL.  
Pydantic используется автоматически для проверки типов.

```python
from fastapi import FastAPI, Path

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int = Path(..., title="ID товара", gt=0)):
    return {"item_id": item_id}
```

* `...` означает обязательный параметр.
* `title`, `gt` → метаданные для документации и валидации.
* Если `item_id` < 1 → 422 Unprocessable Entity.

---

### 2. Query-параметры

Query-параметры передаются после `?` в URL.  
Их можно типизировать через Pydantic-модели с `Depends`.

```python
from fastapi import Query, Depends
from pydantic import BaseModel
from typing import Optional

class ItemQuery(BaseModel):
    limit: int = 10
    offset: int = 0
    search: Optional[str] = None

@app.get("/items/")
async def list_items(query: ItemQuery = Depends()):
    return {"limit": query.limit, "offset": query.offset, "search": query.search}
```

* Можно передавать комплексные параметры через Pydantic.
* Автогенерация документации и валидация всех полей (`limit`, `offset`).

---

### 3. Header-параметры

Заголовки запроса можно валидировать через Pydantic.

```python
from fastapi import Header

@app.get("/headers/")
async def read_headers(x_token: str = Header(..., alias="X-Token")):
    return {"X-Token": x_token}
```

* `alias="X-Token"` → позволяет использовать правильное имя заголовка.
* Параметр `...` делает его обязательным.

---

### 4. Cookie-параметры

Также поддерживаются с помощью `Cookie`.

```python
from fastapi import Cookie

@app.get("/cookies/")
async def read_cookies(session_id: str = Cookie(...)):
    return {"session_id": session_id}
```

* Можно валидировать тип, длину и даже использовать Pydantic модели для сложных структур.

---

### 5. Валидация значений

Все параметры (Path, Query, Header, Cookie) можно валидировать:

```python
@app.get("/users/{user_id}")
async def read_user(
    user_id: int = Path(..., gt=0),
    q: str = Query(None, min_length=3, max_length=50, regex="^[a-zA-Z]+$"),
    x_token: str = Header(..., min_length=8)
):
    return {"user_id": user_id, "q": q, "x_token": x_token}
```

* Path: `gt`, `lt`
* Query: `min_length`, `max_length`, `regex`
* Header: `min_length`, `max_length`

---

### 6. Вложенные и составные параметры

Можно использовать Pydantic-модели для группировки Query/Headers:

```python
class FilterParams(BaseModel):
    category: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]

@app.get("/search/")
async def search_items(filters: FilterParams = Depends()):
    return filters
```

* Позволяет передавать несколько параметров через Query одновременно.
* FastAPI автоматически превращает URL вроде `/search/?category=books&min_price=10` в модель `FilterParams`.

---

## Итог по теме маршрутов:

* **Path, Query, Header, Cookie** полностью типизируются и валидируются.
* Pydantic позволяет использовать **комплексные модели через Depends**.
* Можно валидировать длину, диапазоны, regex, обязательность.
* Вложенные структуры упрощают работу со множеством параметров и документируют API.
