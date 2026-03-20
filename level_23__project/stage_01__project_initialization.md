### Структура проекта (этап 1)

```
aibot/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app + lifespan (подключение redis при старте)
│   ├── config.py                   # настройки через pydantic-settings / .env
│   ├── dependencies.py             # Depends для redis клиента
│   ├── ai/
│   │   ├── __init__.py
│   │   └── generator.py            # клиент OpenAI + промпты
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── filtered_posts.py   # история отфильтровнных постов (пока заглушки)
│   │       ├── generate.py         # ручная генерация (пока заглушка)
│   │       ├── keywords.py         # CRUD ключевых слов (полностью)
│   │       ├── posts.py            # история постов (пока заглушки)
│   │       ├── site_sources.py     # CRUD источников сайтов (полностью)
│   │       └── tg_sources.py       # CRUD источников т-каналов (полностью)
│   ├── news_parser/
│   │   ├── __init__.py
│   │   ├── base.py                 # абстрактный парсер
│   │   ├── sites.py                # парсеры сайтов (habr, vc, etc.)
│   │   └── telegram.py             # Telethon-парсер
│   ├── schemas/                    # все pydantic модели
│   │   ├── __init__.py
│   │   ├── filtered_posts.py
│   │   ├── generate.py
│   │   ├── keywords.py
│   │   ├── posts.py
│   │   ├── site_sources.py
│   │   └── tg_sources.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── keyword_service.py      # бизнес-логика ключевых слов (Redis)
│   │   ├── source_service.py       # бизнес-логика источников (Redis)
│   │   └── dedup_service.py        # проверка дублей (Redis set)
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── parse_sites.py          # задачи парсинга сайтов
│   │   ├── parse_tg.py             # задачи парсинга телеграм-каналов
│   │   ├── filter.py               # задачи фильтрации (по словам и дубликатам)
│   │   ├── generate.py             # задачи генерации статей
│   │   └── publish.py              # задачи публикации статей
│   ├── telegram/
│   │   ├── __init__.py
│   │   └── publisher.py            # Telethon-клиент для публикации
│   └── utils/
│       ├── __init__.py
│       ├── initialization.py       # загрузка начальных данных из settings
│       └── logging.py              # конфигуратор логирования
│
├── celery_app.py                   # создание celery app + autodiscover_tasks
├── celery_worker.py                # точка запуска worker & beat (если отдельно)
├── local_settings.py               # секреты и начальные установки
├── requirements.txt
├── docker-compose.yml
├── README.md
└── .gitignore
```

### 1. requirements.txt 

```bash
pip install fastapi[standard] celery[redis] httpx feedparser

pip freeze > requirements.txt
```

### 2. docker-compose.yml (только Redis на старте)

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis-data:
```

Запуск:

```bash
docker compose up
```

### 3. local_settings.py

`local_settings.py`

```python
# --- Telegram ---------------------------------------------------------------
API_ID = 1234567
API_HASH = "0123456789abcdef0123456789abcdef"
CHANNEL_USERNAME = "@your_news_channel"          # или -1001234567890 (ID канала)

# --- AI SERVICE --------------------------------------------------------------
AI_API_KEY = "---"

# --- Redis -------------------------------------------------------------------
REDIS_URL = "redis://127.0.0.1:6379/0"

# --- Периодичность парсинга (Celery Beat) ------------------------------------
PARSING_INTERVAL_MINUTES = 30

# --- Дефолтные ключевые слова ------------------------------------------------
KEYWORDS = ["python", "ai", "startup", "telegram", "fastapi"]

# --- Telegram-каналы и сайты -------------------------------------------------
TG_SOURCES = [
    # добавим позднее
]

SITE_SOURCES = [
    {"name": "habr", "url": "https://habr.com/ru/rss/"},
    {"name": "rbc", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "vc", "url": "https://vc.ru/rss"},
    {"name": "tproger", "url": "https://tproger.ru/feed/"},
]

```

### 4. config.py

`app/config.py`

```python
from pydantic import BaseModel
from local_settings import *  # noqa

try:
    from local_settings import (
        API_ID, API_HASH, CHANNEL_USERNAME,
        AI_API_KEY, REDIS_URL,
        PARSING_INTERVAL_MINUTES, KEYWORDS,
        TG_SOURCES, SITE_SOURCES,
    )
except ImportError:
    raise ImportError("local_settings.py не найден в корне проекта")


class Settings(BaseModel):
    telegram_api_id: int = API_ID
    telegram_api_hash: str = API_HASH
    target_channel: str = CHANNEL_USERNAME
    ai_api_key: str = AI_API_KEY
    redis_url: str = REDIS_URL
    parsing_interval_minutes: int = PARSING_INTERVAL_MINUTES
    words: list[str] = KEYWORDS
    tg_sources: list[str] = TG_SOURCES
    site_sources: list[dict] = SITE_SOURCES
    log_level: str = "INFO"

settings = Settings.model_validate({})   # просто для валидации типов

```

### 5. `logging.py`

`app/utils/logging.py`

```python
import logging
import sys
from typing import Optional

from app.config import settings


def setup_logging() -> None:
    """Настраивает корневой логгер. Вызывать один раз при старте приложения."""
    level_name = settings.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)

    if not isinstance(log_level, int):
        log_level = logging.INFO
        print(f"WARNING: неизвестный LOG_LEVEL '{level_name}', используется INFO", file=sys.stderr)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Убираем старые handlers, чтобы не дублировать при повторных вызовах
    for h in root.handlers[:]:
        root.removeHandler(h)

    root.addHandler(console_handler)

    # Подавляем слишком шумные логгеры
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "root")
    return logging.getLogger(name)
```

### 6. Инициализация начальных установок

`app/utils/initialization.py`

```python
import redis.asyncio as aioredis

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def initialize_default_settings(redis: aioredis.Redis) -> None:
    """
    Создаёт дефолтные ключевые слова / источники при первом запуске,
    если их ещё нет в Redis.
    """
    # --- Инициализация ключевых слов ---------------------------------------
    default_keywords = settings.words

    count_before = await redis.scard("keywords")
    if count_before == 0:
        logger.info("Redis пуст → добавляем дефолтные ключевые слова")
        for kw in default_keywords:
            await redis.sadd("keywords", kw)
        logger.info(f"Добавлено {len(default_keywords)} дефолтных ключевых слов")
    else:
        logger.debug(f"Ключевые слова уже существуют ({count_before} шт), пропускаем инициализацию")

    # --- Инициализация сайтов -----------------------------------------------
    default_sites = settings.site_sources

    for site in default_sites:
        key = f"site_sources:{site['name']}"
        exists = await redis.exists(key)
        if not exists:
            logger.info("Добавляем дефолтный источник: %s", site['name'])
            await redis.hset(key, mapping={
                "name": site["name"],
                "url": site["url"]
            })
        else:
            logger.debug(f"Источник site_sources: {site['name']} уже существует!")

    # --- Инициализация телеграм-каналов ----------------------------------------
    # Добавим позже

```

### 7. Создаём пул подключений redis

`app/dependencies.py`

```python
import redis.asyncio as aioredis
from fastapi import Request

from app.config import settings   # ← здесь REDIS_URL и другие настройки
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Один глобальный пул подключений (хороший производительный вариант)
# Создаётся один раз при старте приложения
redis: aioredis.Redis | None = None


async def init_redis_pool() -> aioredis.Redis:
    """Инициализация пула подключений к Redis (вызывается в lifespan)"""

    url = settings.redis_url
    logger.debug(f"Инициализация Redis пула: {url}")

    try:
        # Сначала создаём клиента
        redis = await aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            max_connections=20,
            socket_keepalive=True,
        )

        # Проверяем подключение
        pong = await redis.ping()
        logger.info(f"Redis пул инициализирован успешно → PING → {pong}")
        return redis

    except Exception as e:
        logger.critical(f"Критическая ошибка: не удалось подключиться к Redis: {e}")
        redis = None  # явно сбрасываем
        raise RuntimeError(f"Не удалось подключиться к Redis → {e}")


async def get_redis(request: Request) -> aioredis.Redis:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise RuntimeError("Redis is not initialized")
    return redis
```

### 8. main.py (FastAPI + health)

`app/main.py`

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.dependencies import init_redis_pool

from app.utils.logging import setup_logging, get_logger
from app.api.v1 import keywords, site_sources, tg_sources, posts, generate  # импортируем роутеры по мере готовности
from app.utils.initialization import initialize_default_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan-события: запуск при старте / очистка при остановке
    """
    # --- Настройка логирования (один раз при старте) -------------------
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Запуск приложения aibot ...")

    # --- Инициализация Redis -------------------------------------------
    redis_initialized = False
    try:
        redis_pool = await init_redis_pool()
        app.state.redis = redis_pool
        redis_initialized = True
        await initialize_default_settings(redis_pool)
        logger.info("Дефолтные настройки проверены / инициализированы")
    except Exception as e:
        logger.error(f"Ошибка инициализации начальных настроек в Redis: {e}")
        app.state.redis = None
        # не падаем — приложение может продолжить работу

    yield

    # --- Shutdown ----------------------------------------------------
    logger.info("Остановка приложения aibot ...")
    if redis_initialized:
        try:
            redis = getattr(app.state, "redis", None)
            if redis:
                await redis.close()
                await redis.connection_pool.disconnect()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии Redis пула: {e}")
    logger.info("Приложение остановлено")

# --- Само приложение -------------------------------------------------
app = FastAPI(
    title="AI News Telegram Bot",
    description="Автоматизированный новостной канал с AI-генерацией постов",
    lifespan=lifespan
)

# --- Подключаем роутеры (по мере реализации) --------------------------
app.include_router(keywords.router, prefix="/api/v1", tags=["keywords"])
app.include_router(site_sources.router, prefix="/api/v1", tags=["site_sources"])
# app.include_router(tg_sources.router, prefix="/api/v1", tags=["tg_sources"])
# app.include_router(posts.router, prefix="/api/v1", tags=["posts"])
# app.include_router(posts.router, prefix="/api/v1", tags=["filtered_posts"])
# app.include_router(generate.router, prefix="/api/v1", tags=["generate"])


@app.get("/health", response_model=dict, tags=["system"])
async def health_check(request: Request):
    redis = getattr(request.app.state, "redis", None)

    redis_ok = False
    if redis:
        try:
            redis_ok = await redis.ping()
        except Exception:
            redis_ok = False

    status_code = (
        status.HTTP_200_OK if redis_ok
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        content={
            "status": "healthy" if redis_ok else "degraded",
            "redis": "connected" if redis_ok else "disconnected",
        },
        status_code=status_code,
    )
```


### 9. Схемы и эндпойнты ключевых слов

`app/schemas/keywords.py`

```python
from pydantic import BaseModel, Field


class KeywordBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200, strip_whitespace=True)


class KeywordCreate(KeywordBase):
    """Схема для создания нового ключевого слова"""
    pass


class KeywordUpdate(BaseModel):
    """Схема для обновления ключевого слова"""
    keyword: str | None = Field(None, min_length=1, max_length=200)


class KeywordOut(KeywordBase):
    """Схема для вывода ключевого слова"""
    pass  # временная метка убрана
```


`app/api/v1/keywords.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_redis
from app.schemas.keywords import KeywordCreate, KeywordUpdate, KeywordOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/keywords",
    tags=["keywords"],
    responses={404: {"description": "Keyword not found"}},
)


@router.get("/", response_model=list[KeywordOut])
async def list_keywords(
    skip: int = Query(0, ge=0, description="Пропустить N элементов"),
    limit: int = Query(50, ge=1, le=500, description="Максимум элементов"),
    redis = Depends(get_redis),
):
    """Получить список ключевых слов"""
    logger.debug(f"Запрос списка ключевых слов: {skip}, {limit}")

    try:
        keywords = await redis.smembers("keywords")
        if not keywords:
            return []

        return [KeywordOut(keyword=kw) for kw in sorted(keywords)]

    except Exception as e:
        logger.exception("Ошибка при получении списка ключевых слов")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching keywords",
        )


@router.get("/{keyword}", response_model=KeywordOut)
async def get_keyword(keyword: str, redis = Depends(get_redis)):
    """Получить одно ключевое слово по его значению"""

    logger.debug(f"Запрос ключевого слова: {keyword}")

    exists = await redis.sismember("keywords", keyword)
    if not exists:
        raise HTTPException(status_code=404, detail="Keyword not found")

    return KeywordOut(keyword=keyword)


@router.post("/", response_model=KeywordOut, status_code=201)
async def create_keyword(data: KeywordCreate, redis=Depends(get_redis)):
    keyword = data.keyword.strip()
    if not keyword:
        raise HTTPException(422, "Keyword cannot be empty")

    logger.info(f"Попытка создать ключевое слово: {keyword}")

    if await redis.sismember("keywords", keyword):
        raise HTTPException(409, detail=f"Keyword '{keyword}' уже существует")

    try:
        await redis.sadd("keywords", keyword)
        return KeywordOut(keyword=keyword)
    except Exception as e:
        logger.exception(f"Ошибка при создании ключевого слова: {keyword}")
        raise HTTPException(500, "Failed to create keyword")


@router.patch("/{keyword}", response_model=KeywordOut)
async def update_keyword(
    keyword: str,
    data: KeywordUpdate,
    redis = Depends(get_redis),
):
    """Обновить существующее ключевое слово word на new_word (заменить слово)"""

    if not data.keyword:
        raise HTTPException(422, "Nothing to update")

    new_keyword = data.keyword.strip()
    if not new_keyword:
        raise HTTPException(422, "Keyword cannot be empty")

    logger.info(f"Обновление ключевого слова: {keyword} → {new_keyword}")

    # Проверяем существование старого слова
    exists = await redis.sismember("keywords", keyword)
    if not exists:
        raise HTTPException(404, "Keyword not found")

    # Проверяем, не занято ли новое слово
    if new_keyword != keyword and await redis.sismember("keywords", new_keyword):
        raise HTTPException(409, f"Keyword '{new_keyword}' already exists")

    try:
        # Удаляем старое и добавляем новое
        await redis.srem("keywords", keyword)
        await redis.sadd("keywords", new_keyword)

        return KeywordOut(keyword=new_keyword)

    except Exception as e:
        logger.exception(f"Ошибка обновления ключевого слова {keyword} → {new_keyword}")
        raise HTTPException(500, "Failed to update keyword")


@router.delete("/{keyword}", status_code=204)
async def delete_keyword(keyword: str, redis = Depends(get_redis)):
    """Удалить ключевое слово"""

    logger.warning(f"Удаление ключевого слова: {keyword}")

    removed = await redis.srem("keywords", keyword)
    if removed == 0:
        raise HTTPException(404, "Keyword not found")

    await redis.delete(f"keyword:meta:{keyword}")

    logger.info(f"Ключевое слово удалено: {keyword}")
    return None

```
---

### 10. Схемы и эндпойнты источников сайтов

`app/schemas/site_sources.py.py`

```python
from pydantic import BaseModel, Field, HttpUrl


class SiteSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    url: HttpUrl = Field(..., max_length=500)


class SiteSourceCreate(SiteSourceBase):
    """Схема для добавления нового источника"""
    pass


class SiteSourceUpdate(BaseModel):
    """Схема для обновления источника"""
    name: str | None = Field(None, min_length=1, max_length=100)
    url: HttpUrl | None = Field(None, max_length=500)


class SiteSourceOut(SiteSourceBase):
    """Схема для вывода источника"""
    pass

```


`app/api/v1/site_sources.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies import get_redis
from app.schemas.site_sources import SiteSourceCreate, SiteSourceUpdate, SiteSourceOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/site_sources",
    tags=["site_sources"],
    responses={404: {"description": "Source not found"}},
)

@router.get("/", response_model=list[SiteSourceOut])
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_redis),
):
    """Получить список всех источников сайтов"""
    logger.debug(f"Запрос списка источников: skip={skip}, limit={limit}")

    sources = []

    try:
        # Получаем все ключи site_sources
        keys = await redis.keys("site_sources:*")
        if not keys:
            return []  # если ключей нет, возвращаем пустой список

        for key in sorted(keys)[skip : skip + limit]:
            # Декодируем ключ, если он bytes
            key_str = key.decode() if isinstance(key, bytes) else key

            # Берем все поля HASH как словарь str → str
            data = await redis.hgetall(key_str)
            if not data:
                logger.warning(f"HASH ключ пуст или неверный формат: {key_str}")
                continue

            name = data.get("name")
            url = data.get("url")
            if name and url:
                sources.append(SiteSourceOut(name=name, url=url))
            else:
                logger.warning(f"HASH ключ не содержит необходимых полей: {key_str}")

        return sources

    except Exception:
        logger.exception("Ошибка при получении списка источников")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching site sources",
        )


@router.get("/{name}", response_model=SiteSourceOut)
async def get_source(name: str, redis = Depends(get_redis)):
    """Получить один источник сайта по имени"""
    key = f"site_sources:{name}"
    exists = await redis.exists(key)
    if not exists:
        raise HTTPException(404, "Source not found")

    data = await redis.hgetall(key)
    name_s = data.get("name")
    url_s = data.get("url")
    if not name_s or not url_s:
        raise HTTPException(500, "Invalid source data in Redis")

    return SiteSourceOut(
        name=name_s,
        url=url_s
    )


@router.post("/", response_model=SiteSourceOut, status_code=201)
async def create_source(data: SiteSourceCreate, redis = Depends(get_redis)):
    key = f"site_sources:{data.name}"
    if await redis.exists(key):
        raise HTTPException(409, f"Source '{data.name}' already exists")

    try:
        # Конвертируем HttpUrl в str
        await redis.hset(key, mapping={"name": data.name, "url": str(data.url)})
        return SiteSourceOut(name=data.name, url=str(data.url))

    except Exception:
        logger.exception(f"Ошибка при создании источника {data.name}")
        raise HTTPException(500, "Failed to create site source")


@router.patch("/{name}", response_model=SiteSourceOut)
async def update_source(name: str, data: SiteSourceUpdate, redis = Depends(get_redis)):
    key = f"site_sources:{name}"
    if not await redis.exists(key):
        raise HTTPException(404, "Source not found")

    current = await redis.hgetall(key)
    current_name = current.get("name")
    current_url = current.get("url")
    if not current_name or not current_url:
        raise HTTPException(500, "Invalid source data in Redis")

    new_name = data.name.strip() if data.name else current_name
    new_url = str(data.url) if data.url else current_url

    if new_name != name and await redis.exists(f"site_sources:{new_name}"):
        raise HTTPException(409, f"Source '{new_name}' already exists")

    try:
        if new_name != name:
            await redis.delete(key)
            key = f"site_sources:{new_name}"

        await redis.hset(key, mapping={"name": new_name, "url": new_url})
        return SiteSourceOut(name=new_name, url=new_url)

    except Exception:
        logger.exception(f"Ошибка при обновлении источника {name} → {new_name}")
        raise HTTPException(500, "Failed to update site source")


@router.delete("/{name}", status_code=204)
async def delete_source(name: str, redis = Depends(get_redis)):
    key = f"site_sources:{name}"
    removed = await redis.delete(key)
    if removed == 0:
        raise HTTPException(404, "Source not found")

    logger.info(f"Источник сайта удалён: {name}")
    return None

```