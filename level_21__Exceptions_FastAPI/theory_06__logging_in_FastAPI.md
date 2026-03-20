## Логирование ошибок

### 1. Что такое логирование

**Логирование (logging)** — это процесс записи информации о работе приложения в специальные журналы (логи).

Логи позволяют фиксировать:

* события внутри системы;
* возникающие ошибки;
* входящие запросы;
* состояние приложения в момент сбоя.

В отличие от сообщений, возвращаемых пользователю, логи предназначены **исключительно для разработчиков и администраторов системы**.

---

### 2. Зачем нужно логирование

Без логирования анализ проблем в приложении становится значительно сложнее.

Логи помогают:

* находить причины ошибок;
* анализировать поведение пользователей;
* отслеживать сбои внешних сервисов;
* расследовать инциденты;
* контролировать работу системы в production.

Например, если пользователь сообщает о проблеме, разработчик может открыть лог-файл и увидеть:

```
ERROR - Database connection failed
Traceback ...
```

Это значительно ускоряет диагностику проблемы.

---

### 3. Уровни логирования

В Python используется несколько стандартных уровней логирования.

| Уровень  | Назначение                                   |
| -------- | -------------------------------------------- |
| DEBUG    | подробная информация для разработки          |
| INFO     | обычные события работы системы               |
| WARNING  | потенциальные проблемы                       |
| ERROR    | ошибки, не приводящие к остановке приложения |
| CRITICAL | серьёзные сбои системы                       |

Пример:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Application started")
logger.warning("Cache is almost full")
logger.error("Database connection failed")
```

---

### 4. Базовая настройка логирования

Самый простой способ настроить логирование:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)
```

Теперь любое сообщение будет выглядеть примерно так:

```
2025-03-12 10:22:31 [ERROR] api: Database connection failed
```

---

### 5. Логирование ошибок

Особенно важно записывать **исключения**.

Для этого используется метод `logger.exception()`.

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = 10 / 0
except Exception:
    logger.exception("Calculation failed")
```

Метод `exception()` автоматически добавляет **traceback**, что делает лог гораздо полезнее для диагностики.

---

### 6. Логирование в middleware

Middleware — удобное место для записи неожиданных ошибок.

Пример:

```python
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("api")

async def error_logging_middleware(request: Request, call_next):

    try:
        return await call_next(request)

    except Exception as exc:

        logger.exception("Unhandled server error")

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "Unexpected server error"
            }
        )
```

Таким образом:

* пользователь получает безопасный ответ
* разработчик получает подробную запись в логах

---

### 7. Централизованная конфигурация логирования

В реальных проектах настройки логирования обычно выносят в **отдельный файл конфигурации**.

Это позволяет:

* не дублировать код;
* централизованно менять формат логов;
* легко добавлять запись в файлы или системы мониторинга.

---

### 8. Структура проекта

Пример организации проекта с логированием:

```
app/
│
├─ main.py
│
├─ core/
│   └─ logging_config.py
│
├─ middleware/
│   └─ error_middleware.py
│
├─ exceptions/
│   ├─ exceptions.py
│   └─ handlers.py
│
├─ routers/
│   └─ users.py
│
└─ services/
```

Файл `logging_config.py` отвечает за настройку логирования.

---

### 9. Файл конфигурации логирования

`core/logging_config.py`

```python
import logging


def setup_logging():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
```

---

### 10. Подключение логирования в main.py

Теперь достаточно вызвать функцию при запуске приложения.

```python
from fastapi import FastAPI
from core.logging_config import setup_logging

app = FastAPI()

setup_logging()
```

После этого логирование будет доступно во всех модулях.

---

### 11. Использование логгера в других файлах

В любом модуле проекта можно получить логгер следующим образом:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("User created")
logger.error("Payment failed")
```

Имя логгера автоматически соответствует имени модуля.

---

### 12. Итоговая схема обработки ошибок

В реальном приложении система обработки ошибок обычно выглядит так:

```
Request
   │
   ▼
Middleware
   │
   ▼
Router / Business Logic
   │
   ▼
Exception Handlers
   │
   ▼
Response
   │
   ▼
Logging System
```

Таким образом:

* **middleware** перехватывает неожиданные ошибки;
* **exception handlers** обрабатывают известные ошибки;
* **logging** сохраняет информацию о проблемах для анализа.


