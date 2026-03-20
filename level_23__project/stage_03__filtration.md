Фильтрация "сырых" новостей включает в себя два процесса:
1. Фильтрация `title` и `summary` по ключевым словам,
2. Дедупликация (исключение повторной публикации).

Если по первому пункты всё ясно, то для реализации второго пункта сначала надо определиться с критериями.  
Реализация строго семантического сравнения - задача для ещё одного проекта.  
Поэтому, остановимся на относительно простой реализации:
* нормализация `title` и `summary`
  * привести к lower()
  * удалить пунктуацию
  * убрать лишние пробелы
* хешируем результат нормализации

Хеши нормализованных фильтрованных постов мы будем хранить в отдельном списке в течении одной недели.

#### Пример нормализации текста

```python
import hashlib
import re

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def generate_content_hash(title: str, summary: str | None = None) -> str:
    base = f"{title} {summary or ''}"
    normalized = normalize_text(base)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

#### Пример поиска ключевого слова в тексте

```python
def is_have_keyword(title: str, summary: str, keywords: list[str]):
    text = f"{title} {summary}".lower()
    return any(word.lower() in text for word in keywords)
```

Теперь, обсудив критерии фильтрации, можем переходить её непосредственной реализации в коде.

### 1. Сервис фильтрации постов

`app/services/keyword_service.py`

```python
def get_all_keywords(redis) -> list[str]:
    """
    Возвращает полный список ключевых слов
    """
    keywords = redis.smembers("keywords")
    return sorted(
        k.decode() if isinstance(k, bytes) else k
        for k in keywords
    )

def matches_keywords(redis, news: dict) -> bool:
    """
    Проверяет, содержит ли новость хотя бы одно ключевое слово.
    Ищем в title и summary.
    """
    keywords = get_all_keywords(redis)

    if not keywords:
        return True  # если фильтр пуст — пропускаем всё

    text = f"{news['title']} {news.get('summary', '')}".lower()

    return any(word.lower() in text for word in keywords)

```

### 2. Обновляем эндпойнт `list_keywords` в `app/api/v1/keywords.py`

Благодаря выделению получения списка ключевых слов из Redis, мы можем упростить эндпойнт:

```python
from starlette.concurrency import run_in_threadpool

from app.redis_sync import get_sync_redis
from app.services.keyword_service import get_all_keywords


@router.get("/", response_model=list[KeywordOut])
async def list_keywords(
    skip: int = Query(0, ge=0, description="Пропустить N элементов"),
    limit: int = Query(50, ge=1, le=500, description="Максимум элементов"),
    redis = Depends(get_sync_redis),
):
    """Получить список ключевых слов"""
    logger.debug(f"Запрос списка ключевых слов: {skip}, {limit}")

    try:
        keywords = await run_in_threadpool(get_all_keywords, redis)
        return [KeywordOut(keyword=kw) for kw in sorted(keywords)]

    except Exception as e:
        logger.exception("Ошибка при получении списка ключевых слов")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching keywords",
        )
```

❗ Обязательно проверяем изменённый эндпойнт!


### 3. Создаём сервис дедупликации

`app/services/dedup_service.py`

```python
import hashlib
import re

PUBLISHED_TTL = 7 * 24 * 60 * 60  # 1 неделя
FILTERED_TTL = 60 * 60  # 1 час


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def generate_content_hash(title: str, summary: str | None = None) -> str:
    base = f"{title} {summary or ''}"
    normalized = normalize_text(base)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def is_duplicate(redis, content_hash: str) -> bool:
    return redis.exists(f"published_hash:{content_hash}") == 1


def mark_as_published(redis, content_hash: str):
    redis.set(
        f"published_hash:{content_hash}",
        1,
        ex=PUBLISHED_TTL,
    )


def save_filtered(redis, news: dict, content_hash: str):
    redis.hset(
        f"filtered_news:{content_hash}",
        mapping={
            "title": news["title"],
            "url": news.get("url", ""),
            "summary": news.get("summary", ""),
            "source": news["source"],
            "published_at": news["published_at"],
        },
    )
    # --- Добавляем TTL ключ сроком на 1 час: 60 * 60 -----------------
    redis.expire(f"filtered_news:{content_hash}", FILTERED_TTL)

```

### 4. Собираем всё в один сервис фильтрации `filter_service`

`app/services/filter_service.py`

```python
from app.services.dedup_service import (
    generate_content_hash,
    is_duplicate,
    save_filtered,
)
from app.services.keyword_service import matches_keywords


def process_posts(redis, news: dict) -> bool:
    """
    Возвращает True, если новость прошла фильтрацию и сохранена.
    """

    # --- 1 фильтр по ключевым словам -------------------------------------
    if not matches_keywords(redis, news):
        return False

    # --- 2 генерация hash ------------------------------------------------
    content_hash = generate_content_hash(
        news["title"],
        news.get("summary"),
    )

    # --- 3 дедупликация --------------------------------------------------
    if is_duplicate(redis, content_hash):
        return False

    # --- 4 сохранить как отфильтрованную ---------------------------------
    save_filtered(redis, news, content_hash)

    return True

```

### 5. Создаём задачу фильтрации `filter.py`

`app/tasks/filter.py`

```python
import hashlib
from celery import shared_task

from app.redis_sync import get_sync_redis
from app.services.keyword_service import get_all_keywords  # сервис для ключевых слов
from app.utils.logging import get_logger

logger = get_logger(__name__)

FILTERED_TTL = 60 * 60  # 1 час
DUP_TTL = 7 * 24 * 60 * 60  # 1 неделя для индекса хешей

@shared_task(bind=True, name="filter_posts", max_retries=2)
def filter_posts_task(self, previous_results: list | None = None):

    """
    Задача фильтрации сырых новостей.
    Берёт новости из news:raw:*, фильтрует по ключевым словам и дедупликации,
    сохраняет отфильтрованные в news:filtered:*
    """

    redis = get_sync_redis()

    try:
        # --- получаем ключи сырых новостей ---
        keys = redis.keys("news:raw:*")
        if not keys:
            logger.info("Сырых новостей нет")
            return 0

        # --- получаем список ключевых слов ---
        keywords = get_all_keywords(redis)
        keywords = set(kw.lower() for kw in keywords)

        processed = 0

        for key in keys:
            data = redis.hgetall(key)
            if not data:
                continue

            title = data.get("title", "")
            summary = data.get("summary", "")
            source = data.get("source")
            published_at = data.get("published_at")

            content = f"{title} {summary}".lower()
            logger.info(f"[{source}] Пост: {title[:50]}..., проверяем на ключевые слова")

            # --- фильтр по ключевым словам ---
            if keywords:
                if any(kw in content for kw in keywords):
                    logger.info(f"[{source}] Прошёл фильтр по ключевым словам")
                else:
                    logger.info(f"[{source}] НЕ прошёл фильтр по ключевым словам")
                    continue

            # --- дедупликация по хешу ---
            hash_digest = hashlib.md5(content.encode()).hexdigest()
            dup_key = f"news:dup:{hash_digest}"

            if redis.exists(dup_key):
                logger.debug(f"[{source}] Пропущено, дубликат {hash_digest}")
                continue  # уже есть, пропускаем

            # --- сохраняем фильтрованную новость ---
            filtered_key = f"news:filtered:{source}:{published_at}"
            redis.hset(
                filtered_key,
                mapping={
                    "title": title,
                    "url": data.get("url", ""),
                    "summary": summary,
                    "source": source,
                    "published_at": published_at,
                },
            )
            redis.expire(filtered_key, FILTERED_TTL)
            logger.info(f"[{source}] Сохранена фильтрованная новость: {title[:50]}...")

            # --- помечаем как обработанную (дубликат) ---
            # await redis.set(dup_key, 1, ex=DUP_TTL)
            redis.hset(
                dup_key,
                mapping={
                    "hash": hash_digest,
                    "title": title,
                    "summary": summary,
                    "source": data.get("source"),
                    "published_at": data.get("published_at"),
                },
            )
            redis.expire(dup_key, DUP_TTL)

            processed += 1

        logger.info(f"Отфильтровано и сохранено: {processed}")
        return processed

    except Exception as e:
        logger.error("Критическая ошибка в задаче фильтрации", exc_info=True)
        raise self.retry(exc=e, countdown=30)

```

### 6. Добавляем новую задачу в `celery_app.py`

```python
    include=[
        "app.tasks.parse_sites",
        "app.tasks.filter",
    ],
```

### 7. Добавляем новую задачу в `run_pipeline.py`

И ещё отладочную информацию в логи.  

(❗ полезно будет сравнить два окна в PyCharm, чтобы увидеть изменения)

```python
from celery import group, chain

from celery_app import celery_app
from app.tasks.parse_sites import parse_site_task
from app.tasks.filter import filter_posts_task
from app.redis_sync import get_sync_redis


def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]


def main():
    # --- Парсинг -----------------------------------------------------
    source_names = get_all_source_names()

    if not source_names:
        print("Нет источников")
        return

    parse_group = group(
        parse_site_task.s(source_name=name)
        for name in source_names
    )

    result = parse_group.apply_async()

    print("Задачи запущены. Ждём результата...")

    total = result.get(timeout=300)  # ждём завершения всех
    print(f"Результаты: {total}")
    print(f'Всего сохранено "сырых" постов: {sum(total)}')
    
    # --- Фильтрация --------------------------------------------------

    filter_result = filter_posts_task.apply_async()
    print("Фильтрация запущена. Ждём результата...")

    filtered_count = filter_result.get(timeout=180)
    print(f"Отфильтровано: {filtered_count}")


if __name__ == "__main__":
    main()
```

### 8. Добавляем эндпойнт просмотра отфильтрованных новостей

#### 8.1. Схема для вывода отфильтрованных новостей

`app/schemas/filtered_posts.py`:

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class NewsItemOut(BaseModel):
    title: str
    url: HttpUrl | None = None
    summary: str | None = None
    source: str
    published_at: datetime
```


#### 8.2. Эндпойнт для просмотра отфильтрованных новостей

`app/api/v1/filtered_posts.py`:

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime

from app.dependencies import get_redis
from app.schemas.posts import PostsItemOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/filtered_posts",
    tags=["filtered_posts"],
    responses={404: {"description": "Posts not found"}},
)

@router.get("/", response_model=list[PostsItemOut])
async def list_filtered_posts(
    skip: int = Query(0, ge=0, description="Пропустить N элементов"),
    limit: int = Query(50, ge=1, le=500, description="Максимум элементов"),
    redis = Depends(get_redis),
):
    """Получить список свежих новостей из Redis"""
    try:
        keys = await redis.keys("news:filtered:*")
        if not keys:
            return []

        # сортируем по дате публикации (из ключа)
        keys_sorted = sorted(keys, reverse=True)[skip : skip + limit]
        news_list = []

        for key in keys_sorted:
            if isinstance(key, bytes):
                key = key.decode()

            data = await redis.hgetall(key)
            if not data:
                continue

            # приводим published_at к datetime
            pub_at_raw = data.get("published_at")
            if pub_at_raw:
                pub_at = datetime.fromisoformat(pub_at_raw)
            else:
                pub_at = None

            news_list.append(
                PostsItemOut(
                    title=data.get("title", ""),
                    url=data.get("url") or None,
                    summary=data.get("summary"),
                    source=data.get("source", ""),
                    published_at=pub_at,
                )
            )

        return news_list

    except Exception:
        logger.exception("Ошибка при получении свежих новостей")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching fresh news",
        )
```

#### 8.3. Снимаем комментарий в строке подключения роутера в `main.py`

```python
app.include_router(filtered_posts.router, prefix="/api/v1", tags=["filtered_posts"])

```

### 9. Добавим эндпойнт для просмотра истории отфильтрованных постов

Мы договорились, что будет сохранять хэш отфильтрованных постов, чтобы сэкономить на загрузке AI-редактора.  

Полезно было бы получить доступ к этой истории.

`app/schemas/history.py`

```python
from pydantic import BaseModel
from datetime import datetime

class DupHistoryOut(BaseModel):
    hash: str
    title: str
    summary: str
    source: str
    published_at: datetime

```

`app/api/v1/history.py`

```python
from fastapi import APIRouter, Depends, Query
from app.dependencies import get_redis
from app.schemas.history import DupHistoryOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/history",
    tags=["history"],
    responses={404: {"description": "Keyword not found"}},
)

@router.get("/history/dup", response_model=list[DupHistoryOut])
async def get_dup_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_redis),
):
    """
    История дедупликации (хэши заголовков + summary)
    """
    keys = await redis.keys("news:dup:*")
    if not keys:
        return []

    keys = sorted(keys)[skip : skip + limit]

    result = []

    for key in keys:
        data = await redis.hgetall(key)
        if not data:
            continue

        result.append(
            DupHistoryOut(
                hash=data.get("hash"),
                title=data.get("title"),
                summary=data.get("summary"),
                source=data.get("source"),
                published_at=data.get("published_at"),
            )
        )

    return result

```

`main.py`

```python
app.include_router(history.router, prefix="/api/v1", tags=["history"])

```

### 10. Запускаем ОП

❗ Перед тестированием лучше очистить контейнер с Redis!

```bash
celery -A celery_app worker --pool=solo -l info
```

```bash
python run_pipeline.py
```

Должно получиться что-то вроде:

```
Задачи запущены. Ждём результата...
Результаты: [5, 0, 0, 0]
Всего сохранено "сырых" постов: 5
Фильтрация запущена. Ждём результата...
Отфильтровано: 8

```

И просматриваем результаты в двух новых эндпойнтах