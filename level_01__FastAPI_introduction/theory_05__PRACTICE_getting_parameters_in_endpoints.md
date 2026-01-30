## Получение параметров в эндпойнтах

## 1. Path-параметры

Используются для обязательных частей URL.

```python
from fastapi import FastAPI

app = FastAPI()

favorite_books = [
    {"title": "Мастер и Маргарита", "author": "Михаил Булгаков"},
    {"title": "1984", "author": "Джордж Оруэлл"},
    {"title": "Три товарища", "author": "Эрих Мария Ремарк"},
]

@app.get("/books/{item_id}")
async def read_item(item_id: int):
    return {
        "item_id": item_id,
        "book": favorite_books[item_id],
    }
```

**Особенности**:

* Обязательные
* Тип данных можно аннотировать (FastAPI проверит)


Здесь легко получить ошибку, если индекс окажется вне списка.

Поэтому удобно использовать доп. проверку:

```python
from fastapi.responses import HTMLResponse

@app.get("/books/{item_id}")
async def read_item(item_id: int):
    if item_id not in range(len(favorite_books)):
        raise HTTPException(status_code=404, detail="Book not found")
    return {
        "item_id": item_id,
        "book": favorite_books[item_id],
    }
```


---

## 2. Query-параметры

Возможны 2 варианта:
1. Прямое определение через параметры функции (`inferred query parameter`)
2. Явно заданный с опциями и валидацией (`explicit query parameter`)

### 1. Прямое определение через параметры функции

   * FastAPI рассматривает аргументы функции с дефолтным значением как query-параметры.
   * В документации они называются `"query parameters" inferred from function parameters"` 
     * или `"simple query parameters"` в неформальной речи.
* Пример из документации:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
  return {"skip": skip, "limit": limit}
```

[http://127.0.0.1:8000/items/?skip=2&limit=5](http://127.0.0.1:8000/items/?skip=2&limit=5)

[http://127.0.0.1:8000/items/](http://127.0.0.1:8000/items/)


### 2. Явное задание с использованием объекта `Query`

   * FastAPI называет это `"explicit query parameters"`
     * (или просто `"Query parameters with validation and metadata"`).
   * Добавляет возможность валидации и добавления в документацию.
* Пример из документации:

```python
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/items/")
def read_items(
    q: str | None = Query(
        default=None,
        min_length=3,
        max_length=50,
        title="Search query",
        description="Строка для поиска элементов. Минимум 3 символа, максимум 50.",
        example="fastapi"
    )
):
    return {"q": q}

```

[http://127.0.0.1:8000/items/?q=fastapi](http://127.0.0.1:8000/items/?q=fastapi0)

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 3. Тело запроса (Request Body)

Используется для POST, PUT, PATCH и отправки сложных данных (JSON).

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

**Особенности**:

* Работает с Pydantic-моделями
* Позволяет делать валидацию данных
* Можно комбинировать с query-параметрами

**Пример для Swagger:**

```json
{
  "name": "Книга по FastAPI",
  "price": 29.99,
  "is_offer": true
}

```

---

## 4. Form-параметры

Используются при отправке `application/x-www-form-urlencoded` (например, формы HTML).

```python
from fastapi import Form

@app.post("/login/")
def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username}
```

**Примеры рассмотрим позже**

---

## 5. Header-параметры

Позволяют получать данные из HTTP-заголовков.

```python
from fastapi import Header

@app.get("/header/")
def read_header(user_agent: str = Header(...)):
    return {"User-Agent": user_agent}
```

**Примеры рассмотрим позже**


---

## 6. Cookie-параметры

Позволяют получать данные из cookies.

```python
from fastapi import Cookie

@app.get("/cookie/")
def read_cookie(ads_id: str | None = Cookie(default=None)):
    return {"ads_id": ads_id}
```

**Примеры рассмотрим позже**


---

## 7. Комбинирование источников

Можно комбинировать path, query, body, header и cookie:

```python
@app.put("/items/{item_id}")
def update_item(
    item_id: int,                    # path
    item: Item,                      # body
    q: str | None = None,            # query
    user_agent: str = Header(...),   # header
):
    return {"item_id": item_id, "item": item, "q": q, "user_agent": user_agent}
```

**Примеры рассмотрим позже**
