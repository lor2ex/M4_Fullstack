from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers.books import router as books_router
from app.db.repository import init_db, RepositoryError, NotFoundError, AlreadyExistsError
import traceback
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при запуске приложения
    await init_db()
    yield

app = FastAPI(title="Books Async DI API", lifespan=lifespan)

# Подключаем роутеры
app.include_router(books_router)

@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except AlreadyExistsError as ae:
        return JSONResponse(status_code=400, content={"detail": str(ae)})
    except NotFoundError as ne:
        return JSONResponse(status_code=404, content={"detail": str(ne)})
    except RepositoryError as re:
        return JSONResponse(status_code=400, content={"detail": str(re)})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "error": str(e),
                "trace": traceback.format_exc()
            }
        )
