В качестве завершающего аккорда давайте добавим **логирование** в наш `main.py`,  
чтобы все ошибки, а также базовые запросы, фиксировались в указанных логах.

### Изменённый `app/main.py`

```python
import traceback
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers.books import router as books_router
from app.db.repository import init_db, RepositoryError, NotFoundError, AlreadyExistsError


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("books_api")


# Инициализация базы при старте
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up and initializing the database...")
    await init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(title="Books Async DI API", lifespan=lifespan)

# Подключаем роутеры
app.include_router(books_router)


# Middleware для логирования и обработки ошибок
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        logger.info(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code} for {request.method} {request.url}")
        return response
    except AlreadyExistsError as ae:
        logger.warning(f"AlreadyExistsError: {ae}")
        return JSONResponse(status_code=400, content={"detail": str(ae)})
    except NotFoundError as ne:
        logger.warning(f"NotFoundError: {ne}")
        return JSONResponse(status_code=404, content={"detail": str(ne)})
    except RepositoryError as re:
        logger.warning(f"RepositoryError: {re}")
        return JSONResponse(status_code=400, content={"detail": str(re)})
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

```

---

### Что добавлено

1. **`logging.basicConfig`** — базовая конфигурация логирования.
2. **Логирование при старте приложения**.
3. **Логирование каждого запроса и ответа** (метод + URL + статус).
4. **Логирование ошибок**:

   * `AlreadyExistsError`, `NotFoundError`, `RepositoryError` → `warning`
   * все прочие исключения → `error` + стек-трейс.
