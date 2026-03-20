## Глобальная обработка ошибок через middleware

Ранее мы рассмотрели механизм **глобальных обработчиков исключений** (`exception handlers`).
Он позволяет централизованно обрабатывать заранее известные типы ошибок и возвращать пользователю понятные ответы.

Однако в реальных приложениях могут возникать ситуации, когда ошибка **не относится к конкретному типу исключений**  
или вообще не была предусмотрена разработчиком. 

Например:

* ошибка в сторонней библиотеке;
* сбой при работе с базой данных;
* ошибка сериализации данных;
* случайная ошибка в бизнес-логике.

Чтобы приложение не возвращало пользователю технические сообщения или traceback,  
можно добавить **дополнительный уровень защиты — middleware**.

Middleware работает на уровне **обработки HTTP-запроса** и позволяет:

* перехватывать любые необработанные исключения;
* централизованно логировать ошибки;
* возвращать единый формат ответа API.

Таким образом, middleware выполняет роль **глобального защитного слоя**,  
который обрабатывает ошибки, не перехваченные другими механизмами.

Далее рассмотрим, как реализовать такой подход на практике.

---

### 1. Структура проекта

Для middleware обычно выделяют отдельную папку.

```
app/
│
├─ main.py
│
├─ exceptions/
│   ├─ exceptions.py
│   └─ handlers.py
├─ middleware/
│   └─ error_middleware.py
├─ routers/
│   └─ users.py
└─ services/
```

Разделение:

| Модуль     | Назначение            |
| ---------- | --------------------- |
| exceptions | кастомные исключения  |
| handlers   | обработчики ошибок    |
| middleware | глобальные middleware |
| routers    | API endpoints         |

---

### 2. Middleware для обработки ошибок

Создадим файл:

`middleware/error_middleware.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("api")

async def error_handling_middleware(request: Request, call_next):

    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        logger.exception("Unhandled error")

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "Unexpected server error"
            }
        )
```

Этот middleware:

* перехватывает **любую необработанную ошибку**
* пишет её в лог
* возвращает безопасный JSON.

---

### 3. Регистрация middleware

Добавим функцию регистрации.

`middleware/__init__.py`

```python
from fastapi import FastAPI
from .error_middleware import error_handling_middleware


def register_middleware(app: FastAPI):
    app.middleware("http")(error_handling_middleware)
```

---

### 4. Подключение в main.py

Теперь `main.py` остаётся очень чистым.

```python
from fastapi import FastAPI

from middleware import register_middleware
from exceptions.handlers import register_exception_handlers

app = FastAPI()

register_middleware(app)
register_exception_handlers(app)
```

Это **типичный production-подход**.

---

### 5. Где используется middleware

Middleware работает **до и после обработки запроса**.

Порядок выполнения:

```
Request
   ↓
Middleware
   ↓
Router
   ↓
Exception handler (если ошибка)
   ↓
Middleware
   ↓
Response
```

---

### 6. Пример реального middleware

Очень часто middleware используют для:

### логирования запросов

```python
import time
from fastapi import Request

async def logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    print(f"{request.method} {request.url} took {duration:.2f}s")
    return response
```

---

### 7. Сравнение двух подходов "глобализации" ошибок

| Характеристика   | Exception Handler                | Middleware               |
| ---------------- | -------------------------------- | ------------------------ |
| Уровень          | обработка конкретного исключения | обработка всего запроса  |
| Точность         | высокая                          | низкая                   |
| Тип ошибки       | конкретный класс                 | любые ошибки             |
| Использование    | бизнес-логика                    | инфраструктура           |
| Структура ответа | можно настроить для каждого типа | обычно один общий формат |
| Когда вызывается | после возникновения исключения   | вокруг всего запроса     |

---

### 8. Когда использовать Exception Handlers

Лучше подходят для **бизнес-логики**.

Примеры:

* `UserNotFound`
* `NotEnoughBalance`
* `PermissionDenied`
* `OrderAlreadyPaid`

Преимущества:

* чистая бизнес-логика
* понятные HTTP ответы
* гибкость

---

### 9. Когда использовать Middleware

Лучше подходят для **инфраструктурных задач**.

Примеры:

* логирование
* tracing
* измерение времени запроса
* fallback обработка ошибок
* rate limiting
* CORS
* авторизация

---

### 10. Как делают в production

Чаще всего используют **оба подхода одновременно**.

Типичная схема:

```
Request
   ↓
Middleware
   ↓
Router
   ↓
Business Exceptions
   ↓
Exception Handlers
   ↓
Response
```

Middleware ловит **совсем неожиданные ошибки**,
а Exception handlers обрабатывают **известные ошибки системы**.

---

### 11. Production-правило

Очень популярный паттерн:

```
Middleware → ловит неизвестные ошибки
Handlers   → ловят известные ошибки
```

Например:

```
ZeroDivisionError → middleware
UserNotFound → exception handler
NotEnoughBalance → exception handler
```

---

### Итог

* **Exception handlers** — точечная обработка бизнес-ошибок
* **Middleware** — инфраструктурная защита и перехват неожиданных ошибок

Вместе они создают **полноценную систему обработки ошибок**.

