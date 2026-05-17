### 1. Добавляем в init загрузку телеграм-каналов

Имена сайтов у нас уже попадают в Redis автоматически, при первом запуске FastAPI.  

Логично будет туда добавить и имена телеграм-каналов.

`app/utils/initialization.py`

```python
    ...

    # --- Инициализация телеграм-каналов ----------------------------------------
    default_tg_channels = settings.tg_sources

    for tg_channel in default_tg_channels:
        key = f"tg_sources:{tg_channel['name']}"
        exists = await redis.exists(key)
        if not exists:
            logger.info("Добавляем дефолтный источник: %s", tg_channel['name'])
            await redis.hset(key, mapping={
                "name": tg_channel["name"],
            })
        else:
            logger.debug(f"Источник tg_sources: {tg_channel['name']} уже существует!")

```

### 2. Cоздаём схему телеграм-источников

(по аналогии со схемой сайтов, убираем только url)

`app/schemas/tg_sources.py`

```python
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class TgSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)


class TgSourceCreate(TgSourceBase):
    """Схема для добавления нового источника"""
    pass


class TgSourceUpdate(BaseModel):
    """Схема для обновления источника"""
    name: str | None = Field(None, min_length=1, max_length=100)


class TgSourceOut(TgSourceBase):
    """Схема для вывода источника"""
    last_post_at: datetime | None = None

```

### 3. Добавляем `get_all_tg_sources` в `app/services/source_service.py` 

(тоже, действуем по аналогии с `get_all_site_sources)

```python
from app.schemas.tg_sources import TgSourceOut

...


def get_all_tg_sources(redis) -> list[TgSourceOut]:

    sources: list[TgSourceOut] = []

    keys = redis.keys("tg_sources:*")
    if not keys:
        return []

    for key in sorted(keys):
        # Берем все поля HASH как словарь str → str
        data = redis.hgetall(key)
        if not data:
            logger.warning(f"HASH ключ пуст или неверный формат: {key}")
            continue

        name = data.get("name")
        last_post_at = data.get("last_post_at")
        if name:
            sources.append(TgSourceOut(name=name, last_post_at=last_post_at))
        else:
            logger.warning(f"HASH ключ не содержит необходимых полей: {key}")

    return sources

```


### 4. Cоздаём эндпойнты телеграм-источников
(для демонстрации ограничимся только просмотром)


```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_redis
from app.redis_sync import get_sync_redis
from app.services.source_service import get_all_tg_sources
from app.schemas.tg_sources import TgSourceCreate, TgSourceUpdate, TgSourceOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/tg_sources",
    tags=["tg_sources"],
    responses={404: {"description": "Tg source not found"}},
)

@router.get("/", response_model=list[TgSourceOut])
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_sync_redis),
):
    """Получить список всех источников сайтов"""
    logger.debug(f"Запрос списка источников: skip={skip}, limit={limit}")

    try:

        all_sources = await run_in_threadpool(
            get_all_tg_sources, redis
        )
        return all_sources[skip: skip + limit]


    except Exception:
        logger.exception("Ошибка при получении списка источников")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching site sources",
        )
```


### 5. Не забываем раскомментить эндпойнты в `main.py`

```python
# app.include_router(tg_sources.router, prefix="/api/v1", tags=["tg_sources"])

```

### 6. Запускаем FastAPI

Должно отобразиться что-то вроде этого:

```
[2026-03-26 16:18:12] INFO     | app.utils.initialization:48 | Добавляем дефолтный источник: @techmedia
[2026-03-26 16:18:12] INFO     | app.utils.initialization:48 | Добавляем дефолтный источник: @IT_today_ru
```


### 7. Проверяем эндпойнт `tg_sources`

Должно отобразиться что-то вроде этого:

```json
[
  {
    "name": "@IT_today_ru",
    "last_post_at": null
  },
  {
    "name": "@techmedia",
    "last_post_at": null
  }
]
```

### 8. Создаём задачу парсинга телеграм-каналов

Переименовываем `app/tasks/parse.py` в `app/tasks/parse_tg.py`.

```python
from celery import shared_task
from datetime import datetime

from app.config import settings
from app.news_parser.telegram import pars_tg_channel
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def parse_tg_task(self, source_name: str):
    redis = get_sync_redis()
    try:
        source_key = f"tg_sources:{source_name}"
        data = redis.hgetall(source_key)

        if not data:
            logger.warning(f"[{source_name}] Источник не найден")
            return 0

        # source_url = data["url"]
        last_post_raw = data.get("last_post_at")
        last_post_at = datetime.fromisoformat(last_post_raw) if last_post_raw else None

        logger.info(f"[{source_name}] Запуск парсинга")

        news_items = pars_tg_channel(source_name)

        if not news_items:
            return 0

        news_items.sort(key=lambda x: x["published_at"], reverse=True)

        # --- оставляем только новости, свежее last_post_at ---------------------
        if last_post_at:
            fresh_news = [
                n for n in news_items
                if n.get("published_at") and n["published_at"] > last_post_at
            ]
        else:
            fresh_news = news_items

        # --- ограничиваем число новостей -----------------------------------------
        fresh_news = fresh_news[: settings.max_news_per_source_per_run]

        if not fresh_news:
            logger.info(f"[{source_name}] Нет новых новостей")
            return 0

        # --- записываем "сырые" новости в Redis ---------------------
        for news in fresh_news:
            news_key = f"news:raw:{source_name}:{news['published_at'].isoformat()}"
            redis.hset(
                news_key,
                mapping={
                    "title": news["title"],
                    "url": news.get("link", ""),
                    "summary": news.get("summary", ""),
                    "source": source_name,
                    "published_at": news["published_at"].isoformat(),
                },
            )
            redis.expire(news_key, 3600)

        # --- обновляем дату последнего поста last_post_at --------------
        newest = max(n["published_at"] for n in fresh_news)
        redis.hset(source_key, mapping={"last_post_at": newest.isoformat()})

        logger.info(f"[{source_name}] Сохранено {len(fresh_news)} новых новостей")
        return len(fresh_news)

    except Exception as exc:
        logger.error(f"[{source_name}] Ошибка: {exc}")
        raise self.retry(exc=exc)

```

### 9. Добавляем задачу в `celery_app.py`


```python
        ...
        "app.tasks.parse_tg",
        ...

```

### 10. Добавляем обработку задачи в `run_pipeline.py`

1. Добавляем новые импорт и функцию

```python
...
from app.tasks.parse_tg import parse_tg_task

...


def get_all_tg_names():
    redis = get_sync_redis()
    keys = redis.keys("tg_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]
```

2. И изменяем начало функции `main`

```python
def main():
    source_site_names = get_all_source_names()
    source_tg_names = get_all_tg_names()

    if not (source_site_names or source_tg_names):
        print("Нет источников")
        return

    parse_group = group(
        [parse_site_task.s(source_name=name) for name in source_site_names] + 
        [parse_tg_task.s(source_name=name) for name in source_tg_names]
    )

    result = parse_group.apply_async()

    ...


```

### 11. Запускаем ОП

```bash
celery -A celery_app worker --pool=solo -l info
```

```bash
python run_pipeline.py
```
