### Обработка стандартных HTTP-ошибок в FastAPI

Перед тем как говорить о механизмах обработки ошибок в **FastAPI**,  
полезно вспомнить, какие HTTP-коды ответов вообще существуют. 

Эти коды стандартизированы и сообщают клиенту, что произошло с его запросом.

---

### 1. Основные группы HTTP-статусов

HTTP-ответы делятся на несколько категорий в зависимости от первой цифры кода.

| Диапазон    | Категория       | Что означает                                  |
| ----------- | --------------- | --------------------------------------------- |
| **100–199** | Информационные  | Запрос получен и обрабатывается               |
| **200–299** | Успешные ответы | Запрос выполнен успешно                       |
| **300–399** | Перенаправления | Клиент должен выполнить дополнительный запрос |
| **400–499** | Ошибки клиента  | Ошибка в запросе пользователя                 |
| **500–599** | Ошибки сервера  | Сбой на стороне сервера                       |

---

### 2. Часто используемые HTTP-коды

Ниже приведены наиболее распространённые статусы, которые используются в API.

| Код     | Название              | Описание                                      |
|---------|-----------------------|-----------------------------------------------|
| **100** | Continue              | Сервер получил заголовки запроса              |
| **200** | OK                    | Запрос успешно обработан                      |
| **201** | Created               | Ресурс успешно создан                         |
| **204** | No Content            | Успешный ответ без тела                       |
| **301** | Moved Permanently     | Ресурс перемещён                              |
| **302** | Found                 | Временное перенаправление                     |
| **400** | Bad Request           | Некорректный запрос                           |
| **401** | Unauthorized          | Требуется авторизация                         |
| **403** | Forbidden             | Доступ запрещён                               |
| **404** | Not Found             | Ресурс не найден                              |
| **409** | Conflict              | Конфликт данных                               |
| **422** | Unprocessable Entity  | Ошибка валидации данных                       |
| **429** | Too Many Requests     | Слишком много запросов за короткий промежуток |
| **500** | Internal Server Error | Внутренняя ошибка сервера                     |
| **503** | Service Unavailable   | Сервис временно недоступен                    |

В **FastAPI** многие из этих ошибок можно обрабатывать автоматически или явно возвращать в коде.

---

### 3. Генерация стандартной ошибки

В FastAPI стандартные HTTP-ошибки обычно создаются с помощью исключения `HTTPException`.

Пример — возврат ошибки **404**, если ресурс отсутствует.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

products = {
    1: "Laptop",
    2: "Keyboard",
    3: "Mouse"
}

@app.get("/products/{product_id}")
async def get_product(product_id: int):

    if product_id not in products:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {"product": products[product_id]}
```

Если клиент запросит `/products/10`, сервер вернёт:

```json
{
  "detail": "Product not found"
}
```

---

### 4. Ошибка доступа (403)

Иногда пользователь существует, но не имеет прав для доступа к ресурсу.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/admin")
async def admin_panel(user_role: str):

    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return {"message": "Welcome to admin panel"}
```

Такой код сообщает клиенту, что **запрос корректный, но доступ запрещён**.

---

### 5. Ошибка некорректного запроса (400)

Когда данные запроса не соответствуют ожидаемым параметрам, можно вернуть статус **400 Bad Request**.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/discount")
async def get_discount(percent: int):

    if percent < 0 or percent > 100:
        raise HTTPException(
            status_code=400,
            detail="Discount must be between 0 and 100"
        )

    return {"discount": percent}
```

---

### 6. Ошибка сервера (500)

Иногда происходит непредвиденная ошибка. В таких случаях лучше вернуть общий ответ, не раскрывая детали реализации.

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/process")
async def process_data():

    try:
        data = {"value": 5}
        result = data["missing_key"]

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Server encountered an error"
        )
```

Такой подход предотвращает утечку внутренней информации.

---

### 7. Автоматические ошибки FastAPI

FastAPI также автоматически генерирует некоторые HTTP-ошибки.

Например, если передать неправильный тип параметра:

```python
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}
```

Запрос:

```
/items/abc
```

приведёт к ответу:

```
422 Unprocessable Entity
```

Это происходит благодаря встроенной системе валидации **Pydantic**.

---

### Итог

Стандартные HTTP-ошибки позволяют API:

* сообщать клиенту причину проблемы;
* придерживаться общепринятых стандартов;
* упрощать отладку и интеграцию.

В **FastAPI** такие ошибки обычно создаются через `HTTPException`,  
а часть из них (например **422**) генерируется автоматически системой валидации.

