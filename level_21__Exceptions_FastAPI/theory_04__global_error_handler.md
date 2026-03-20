### 1. Зачем нужен глобальный обработчик ошибок

В крупных приложениях писать `try/except` или `raise HTTPException` в каждом маршруте неудобно.  

Глобальный обработчик позволяет:

* централизованно перехватывать ошибки;
* возвращать единый формат ответа для всех исключений;
* логировать ошибки в одном месте;
* поддерживать согласованную политику обработки разных типов ошибок.

---

### 2. Размещение пользовательских исключений

В реальных проектах обработчики ошибок обычно **не размещают в `main.py`**.
Их выносят в отдельный модуль и **регистрируют при инициализации приложения**.  
Это делает код чище и лучше масштабируется.

Обычно структура проекта выглядит так:

```
project/
│
├─ app/
│   ├─ main.py
│   ├─ exceptions.py
│   ├─ handlers.py
│   └─ routers/
│       └─ users.py
```

---

### 3. Файл с исключениями

Создаём файл `exceptions.py`.

```python
class NotEnoughBalanceException(Exception):

    def __init__(self, detail: str = "Not enough balance"):
        self.detail = detail
        self.status_code = 400
```

Это **кастомное исключение**, которое можно вызывать в любой части приложения.

---

### 4. Файл обработчиков ошибок

Создаём `handlers.py`.

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from .exceptions import NotEnoughBalanceException


async def balance_exception_handler(request: Request, exc: NotEnoughBalanceException):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "BalanceError",
            "message": exc.detail
        }
    )
```

Здесь мы **просто описываем функцию**, но пока её нигде не подключаем.

---

### 5. Регистрация обработчиков

Теперь создадим функцию регистрации обработчиков.

`handlers.py`

```python
from fastapi import FastAPI
from .exceptions import NotEnoughBalanceException
from .handlers import balance_exception_handler


def register_exception_handlers(app: FastAPI):

    app.add_exception_handler(
        NotEnoughBalanceException,
        balance_exception_handler
    )
```

Это распространённый production-подход.

---

### 6. Подключение в `main.py`

Теперь в `main.py` всё выглядит аккуратно:

```python
from fastapi import FastAPI
from handlers import register_exception_handlers

app = FastAPI()

register_exception_handlers(app)
```

Всё.
Теперь обработчик будет работать **во всём приложении**.

---

### 7. Использование исключения в коде

Теперь его можно вызывать где угодно.

Например в роутере:

```python
from fastapi import APIRouter
from exceptions import NotEnoughBalanceException

router = APIRouter()

@router.get("/buy")
async def buy():

    balance = 10
    price = 100

    if balance < price:
        raise NotEnoughBalanceException("You don't have enough money")

    return {"status": "success"}
```

FastAPI автоматически:

1. поймает исключение
2. передаст его обработчику
3. вернёт JSON ответ

---

### 8. Что происходит внутри FastAPI

Когда мы пишем:

```python
app.add_exception_handler(ExceptionType, handler)
```

мы говорим FastAPI:

> если где-то возникнет `ExceptionType`, вызывай `handler`.

Поэтому **обработчик сработает независимо от того, в каком роутере возникла ошибка**.

---

### 9. Итоговая архитектура

```
app/
│
├─ main.py
├─ exceptions.py
├─ handlers.py
├─ services/
├─ routers/
│   ├─ users.py
│   └─ payments.py
```

* `exceptions.py` — кастомные исключения
* `handlers.py` — обработчики
* `main.py` — регистрация
* `routers` — использование исключений

Это делает систему:

* масштабируемой
* легко поддерживаемой
* понятной для команды

