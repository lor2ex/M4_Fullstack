## 1. Зачем нужна обработка ошибок?

Представим API, в котором отсутствует обработка ошибок.  

Пользователь отправляет некорректный запрос и вместо понятного ответа получает длинный Python traceback. 

Пользователь в панике.  
 
И, скорее всего, он выберет себе "менее пугающий" ресурс.

Поэтому, корректная обработка ошибок выполняет сразу несколько задач:

* делает интерфейс приложения понятным для пользователей;
* скрывает внутреннюю реализацию системы;
* помогает разработчикам быстрее находить проблемы.

Фактически обработка ошибок — это механизм, который помогает приложению  
**корректно реагировать на непредвиденные ситуации**.

---

## 2. Типы ошибок

Условно, все виды ошибок можно классифицировать как
* ожидаемые ошибки
* и неожиданные (случайные) ошибки

### 2.1. Ожидаемые ошибки

Это ситуации, которые можно заранее предусмотреть.

Например:

* пользователь отправил неверные данные;
* запрашиваемый объект отсутствует;
* пользователь не имеет доступа к ресурсу.

Такие ошибки обычно обрабатываются на уровне логики приложения.

Пример:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

fake_users = {1: "Alice", 2: "Bob", 3: "Charlie"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = fake_users.get(user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User with this ID does not exist"
        )

    return {"user_id": user_id, "name": user}
```

Если пользователь запросит несуществующий ID, API вернёт понятный ответ.

---

### 2.2. Неожиданные ошибки

Иногда происходят проблемы, которые сложно предсказать:

* база данных недоступна;
* внешний сервис не отвечает;
* ошибка в бизнес-логике.

В таких случаях важно не просто остановить выполнение программы, а **аккуратно обработать ситуацию**.

Пример:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/calculate")
async def calculate(value: int):
    try:
        result = 100 / value
        return {"result": result}

    except ZeroDivisionError:
        raise HTTPException(
            status_code=400,
            detail="Value cannot be zero"
        )
```

Такой подход предотвращает "падение" приложения.

---

## 3. Основные принципы обработки ошибок

### 3.1. Понятные сообщения для пользователя

Пользователь не должен видеть технические детали системы.

Вместо:

```
Traceback (most recent call last)
ZeroDivisionError: division by zero
```

Лучше показать понятное сообщение:

```
Invalid input value
```

Пример:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/orders/{order_id}")
async def get_order(order_id: int):

    if order_id < 1:
        raise HTTPException(
            status_code=400,
            detail="Order ID must be positive"
        )

    return {"order_id": order_id}
```

---

### 3.2. Логирование ошибок

Ошибки полезно записывать в лог-файлы. Это помогает:

* отслеживать сбои;
* анализировать проблемы;
* расследовать инциденты.

Пример логирования:

```python
import logging
from fastapi import FastAPI

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

@app.get("/divide")
async def divide(a: int, b: int):

    try:
        result = a / b
        return {"result": result}

    except Exception as error:
        logger.exception("Calculation failed")
        return {"message": "Something went wrong"}
```

Метод `logger.exception()` автоматически записывает traceback.

---

### 3.3. Не раскрывайте внутреннюю информацию

При информировании пользователя об ошибке важно чётко разделять:
* что сообщать (показывать) пользователю при возникновении ошибки
* и что должен видеть исключительно разработчик.

Одна из распространённых ошибок — показывать пользователю слишком много деталей.

Это может раскрыть:

* структуру проекта;
* используемые библиотеки;
* внутренние переменные.

Плохой пример:

```python
@app.get("/unsafe")
async def unsafe():
    data = {}
    return data["missing_key"]
```

Если ошибка не обработана, сервер вернёт стек вызовов.

Лучше перехватывать подобные ситуации.

---

## 4. Практические сценарии

### 4.1. Кастомная HTML-страница ошибки

Иногда API используется внутри веб-сайта, и пользователю лучше показать красивую страницу.

Пример:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/page", response_class=HTMLResponse)
async def example_page():

    html_content = """
    <html>
        <body>
            <h2>Страница временно недоступна</h2>
            <p>Попробуйте обновить страницу позже.</p>
        </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=503)
```

---

### 4.2. Разные сообщения для разработки и продакшена

Во время разработки полезно видеть подробности ошибок.  
Но в рабочей среде такие данные лучше скрывать.

Пример:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

DEBUG = False

@app.get("/debug")
async def debug_example():

    try:
        numbers = [1, 2, 3]
        return numbers[10]

    except IndexError as error:

        if DEBUG:
            raise HTTPException(
                status_code=500,
                detail=f"Debug info: {error}"
            )

        raise HTTPException(
            status_code=500,
            detail="Unexpected server error"
        )
```

---

### 4.3. Глобальный обработчик ошибок

Иногда полезно централизованно обрабатывать ошибки во всём приложении.

Это позволяет:

* поддерживать единый формат ответа;
* не дублировать код;
* легче поддерживать API.

Пример глобального обработчика:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):

    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error"
        }
    )
```

Теперь любое необработанное исключение будет возвращать понятный JSON-ответ.

---

### 4.4. Собственные классы исключений

Иногда удобно создавать **кастомные исключения** для бизнес-логики.

Например, если пользователь пытается заказать товар, которого нет на складе.

```python
class ProductOutOfStock(Exception):
    pass
```

Использование:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

class ProductOutOfStock(Exception):
    pass


@app.exception_handler(ProductOutOfStock)
async def product_out_of_stock_handler(request: Request, exc: ProductOutOfStock):

    return JSONResponse(
        status_code=400,
        content={"message": "Product is out of stock"}
    )


@app.get("/buy")
async def buy_product():

    stock = 0

    if stock == 0:
        raise ProductOutOfStock()

    return {"message": "Purchase successful"}
```

Такой подход помогает **логически разделять разные типы ошибок**.

---

### 4.5. Возврат стандартной структуры ошибок

В крупных API часто используют **единый формат ответа при ошибках**.

Например:

```json
{
  "error": {
    "code": 404,
    "message": "User not found"
  }
}
```

Пример реализации:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int):

    if user_id != 1:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": 404,
                    "message": "User not found"
                }
            }
        )

    return {"user_id": 1, "name": "Alice"}
```

Это облегчает работу:

* фронтенд-разработчикам;
* мобильным приложениям;
* интеграциям с другими сервисами.

---

## Таким образом

Хорошая обработка ошибок делает приложение:

* **удобным для пользователя** — понятные сообщения;
* **безопасным** — отсутствие утечки внутренних данных;
* **удобным для поддержки** — благодаря логированию.
