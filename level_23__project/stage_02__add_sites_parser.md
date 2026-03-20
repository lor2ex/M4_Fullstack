Переходим к созданию основного процесса.

Он управляется Celery, который плохо совместим с пакетом `asyncio`.  
Как вариант, можно внутри каждой задачи запускать корутины со своим собственным `event loop`.    
Однако, большого выигрыша по производительности это вряд ли принесёт.  
А вот сложность в отладке и проблемы утечки памяти, практически, гарантированы.

Поэтому, оба процесса (ОП на Celery и ИНОП на FastAPI) будут разделены ещё и технологически:  
`async` код для FastAPI и обычный sync - для задач Celery.  

И если какие-то функции необходимо использовать в обоих процесса, то
* они изначально будут строго sync,
* а при использовании в FastAPI мы из просто обернём через `run_in_threadpool()`.

### 1. Создаём `sync` подключение к redis

`app/redis_sync`

```python
import redis
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_sync_redis: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    """Ленивая инициализация sync Redis-пула для Celery задач"""
    global _sync_redis

    if _sync_redis is None:
        logger.info("Инициализация sync Redis пула для Celery...")

        _sync_redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=10,           
            socket_connect_timeout=10,  
            retry_on_timeout=True,      
            max_connections=20,
        )

        # Проверка подключения сразу при создании
        try:
            _sync_redis.ping()
            logger.info("sync Redis пул успешно инициализирован и проверен")
        except Exception as e:
            logger.error(f"Не удалось подключиться к sync Redis: {e}")
            _sync_redis = None
            raise RuntimeError(f"Redis connection failed: {e}") from e

    return _sync_redis
```

### 2. Создаём sync парсер получения списка источников

Для парсинга нам потребуется добавить два новых пакета:

```bash
pip install feedparser beautifulsoup4

pip freeze > requirements.txt
```

`app/news_parser/sites.py`

```python
import httpx
import feedparser
from datetime import datetime

from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # Удаляем все картинки
    for img in soup.find_all("img"):
        img.decompose()

    # Удаляем все ссылки целиком
    for a in soup.find_all("a"):
        a.decompose()
    return soup.get_text(strip=True)


def parse_rss(url: str):
     with httpx.Client(timeout=10, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        feed = feedparser.parse(r.text)


        posts = []
        for entry in feed.entries:
            published = None
            # преобразуем дату публикации в объект datetime
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            posts.append({
                "title": entry.title,
                "link": entry.link,
                "summary": html_to_text(entry.summary),
                "published_at": published
            })

        return posts


# выполняем smoke-тест для функции rss-парсинга
if __name__ == "__main__":
    url = "https://habr.com/ru/rss/"
    posts = parse_rss(url)

    for post in posts:
        print(f"{post['published_at']} | {post['title']}")
        print(post['link'])
        print(post['summary'])
        print("-" * 80)
```

Запускаем этот скрипт и проверяем результаты парсинга.


### 3. Рефакторинг эндпойнта отображения списка источников `list_sources()`

### 3.1. При обновлении "сырых" постов нам нужна дата последнего поста `last_post_at`:
   * можно, конечно, делать запрос к Redis и находить самый "свежий" пост,
   * но проще сразу, после парсинга сохранять дату последнего поста конкретного источника
   * и удобнее всего добавить новое поле к списку источников `last_post_at: datetime | None = None`

`app/schemas/site_sources.py`

```python
class SiteSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    url: HttpUrl = Field(..., max_length=500)

class SiteSourceOut(SiteSourceBase):
    """Схема для вывода источника"""
    last_post_at: datetime | None = None
```

Таким образом, словарь источников изменился.

Было:
```python
source = {"name": "habr", "url": "..."}
```

Стало:
```python
source = {"name": "habr", "url": "...", "last_post_at": "..."}
```


### 3.2. Часть эдпойнта выделяем в отдельную sync функцию `get_all_site_sources`

Мы будем её использовать 
* и в эндпонйте `list_sources()`, 
* и в задаче парсинга

Обратите внимание, что эта функция больше не `asunc`!

`app/services/source_service.py`

```python
from app.schemas.site_sources import SiteSourceOut
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_all_site_sources(redis) -> list[SiteSourceOut]:

    sources: list[SiteSourceOut] = []

    keys = redis.keys("site_sources:*")
    if not keys:
        return []

    for key in sorted(keys):
        # Берем все поля HASH как словарь str → str
        data = redis.hgetall(key)
        if not data:
            logger.warning(f"HASH ключ пуст или неверный формат: {key}")
            continue

        name = data.get("name")
        url = data.get("url")
        last_post_at = data.get("last_post_at")
        if name and url:
            sources.append(SiteSourceOut(name=name, url=url, last_post_at=last_post_at))
        else:
            logger.warning(f"HASH ключ не содержит необходимых полей: {key}")

    return sources


if __name__ == "__main__":
    from app.sync_redis import get_sync_redis
    for source in get_all_site_sources(get_sync_redis()):
        print(source)
```

Этот скрипт можно сразу же протестировать:

```
name='habr' url=HttpUrl('https://habr.com/ru/rss/') last_post_at=None
name='rbc' url=HttpUrl('https://rssexport.rbc.ru/rbcnews/news/30/full.rss') last_post_at=None
name='tproger' url=HttpUrl('https://tproger.ru/feed/') last_post_at=None
name='vc' url=HttpUrl('https://vc.ru/rss') last_post_at=None
```

(время `None` потому, что мы ещё не запускали парсинг в проекте)


### 3.3. Корректируем эндпойнт с учётом последнего изменения

* вырезанный фрагмент кода заменяем на функцию `get_all_site_sources`
* в качестве аргумента подаём `get_sync_redis()`
* и оборачиваем эту функцию в `run_in_threadpool`:

```python
        all_sources = await run_in_threadpool(
            get_all_site_sources, sync_redis
        )
```

Важно: не забудьте добавить 3 новых импорта!

`app/api/v1/site_sources.py`

```python
from starlette.concurrency import run_in_threadpool

from app.redis_sync import get_sync_redis
from app.services.source_service import get_all_site_sources

@router.get("/", response_model=list[SiteSourceOut])
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_sync_redis),  # В этом месте именно sync Redis!
):
    """Получить список всех источников сайтов"""
    logger.debug(f"Запрос списка источников: skip={skip}, limit={limit}")

    try:
        all_sources = await run_in_threadpool(
            get_all_site_sources, redis
        )
        return all_sources[skip: skip + limit]

    except Exception:
        logger.exception("Ошибка при получении списка источников")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching site sources",
        )

```

И тут же тестируем эти изменения: [http://127.0.0.1:8000/docs#/site_sources/list_sources_api_v1_site_sources__get](http://127.0.0.1:8000/docs#/site_sources/list_sources_api_v1_site_sources__get)

### 4. Создаём задачу парсинга одного источника

На этапе отладки нам удобно будет уменьшить число новостей.  

#### 4.1. Добавим новый параметр в `local_setting.py`:

```python
MAX_NEWS_PER_SOURCE_PER_RUN = 10
```

#### 4.2. Добавим новый параметр в `config.py`:

```python
class Settings(BaseModel):
    ...
    max_news_per_source_per_run: int = MAX_NEWS_PER_SOURCE_PER_RUN
```

### 5. Создаём задачу парсинга

`app/tasks/parse_sites.py`

```python
from celery import shared_task
from datetime import datetime

from app.config import settings
from app.news_parser.sites import parse_rss
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def parse_site_task(self, source_name: str):
    redis = get_sync_redis()
    try:
        source_key = f"site_sources:{source_name}"
        data = redis.hgetall(source_key)

        if not data:
            logger.warning(f"[{source_name}] Источник не найден")
            return 0

        source_url = data["url"]
        last_post_raw = data.get("last_post_at")
        last_post_at = datetime.fromisoformat(last_post_raw) if last_post_raw else None

        logger.info(f"[{source_name}] Запуск парсинга")

        news_items = parse_rss(source_url)  

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


### 6. Настраиваем Celery для запуска первой задачи

#### 6.1. `celery_app.py`

`app/celery_app.py`

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "news_parser",
    broker=settings.redis_url,     # redis://localhost:6379/0
    backend=settings.redis_url,
    include=[
        # сюда будем добавлять задачи
    ],

)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

```

---

#### 6.2. `celery_worker.py`

Точка входа Celery

```python
from celery_app import celery_app

# чтобы Celery увидел задачи
import app.tasks.parse_sites  # noqa
```
---

#### 6.3. Скрипт запуска всех задач через group

Создадим файл `run_pipeline.py` для ручного запуска задач всего основного процесса (ОП):

```python
from celery import group

from celery_app import celery_app
from app.tasks.parse_sites import parse_site_task
from app.redis_sync import get_sync_redis


def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]


def main():
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
    print(f"Всего сохранено: {sum(total)}")

if __name__ == "__main__":
    main()
```

---

#### 6.4. Добавляем задачу в celery_app:

```python
    ...
    include=[
        "app.tasks.parse_sites",
    ],
    ...

```

---

#### 6.5. Запускаем ОП

```bash
celery -A celery_app worker --pool=solo -l info
```

```bash
python run_pipeline.py
```


Должно быть что-то вроде этого:

```
Задачи запущены. Ждём результата...
Результаты: [10, 10, 10, 10]
Всего сохранено: 40
```

Если проверим эндпойнт http://127.0.0.1:8000/docs#/site_sources/list_sources_api_v1_site_sources__get,  
то увидим, что у наших источников появилось реальное время.


### 7. Последний штрих - добавляем эндпойнт просмотра "сырых" новостей

Простой эндпойнт FastAPI для просмотра **сырых новостей**, которые только что собрал парсер.  
Так как новости хранятся в Redis в ключах:  

```
news:raw:{source_name}:{published_at}
```

мы можем вернуть их списком или по источнику.

---

#### 7.1. Схема для вывода новости

`app/schemas/posts.py`:

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class PostsItemOut(BaseModel):
    title: str
    url: str | None = None
    summary: str | None = None
    source: str
    published_at: datetime
```

---

#### 7.2. Эндпойнт для просмотра новостей

`app/api/v1/posts.py`:

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.dependencies import get_redis
from app.schemas.posts import PostsItemOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
    responses={404: {"description": "Posts not found"}},
)

@router.get("/", response_model=list[PostsItemOut])
async def list_posts(
    source: str | None = Query(None, description="Фильтр по источнику"),
    limit: int = Query(50, ge=1, le=500),
    redis = Depends(get_redis),
):
    """
    Получить список сырых новостей из Redis.
    Если source не указан — все источники.
    """
    try:
        pattern = f"news:raw:{source}:*" if source else "news:raw:*:*"
        keys = await redis.keys(pattern)

        if not keys:
            return []

        # сортировка по дате из ключа (yyyy-mm-ddT...)
        keys_sorted = sorted(keys, reverse=True)[:limit]

        news_list = []
        for key in keys_sorted:
            if isinstance(key, bytes):
                key = key.decode()

            data = await redis.hgetall(key)
            if not data:
                continue

            try:
                news_list.append(PostsItemOut(
                    title=data["title"],
                    url=data.get("url"),
                    summary=data.get("summary"),
                    source=data["source"],
                    published_at=data["published_at"]
                ))
            except KeyError as e:
                logger.warning(f"Некорректная новость в Redis {key}: {e}")
                continue

        return news_list

    except Exception as e:
        logger.exception("Ошибка при получении новостей")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching news"
        )

```

---

#### 7.3. Подключение роутера в `main.py`

Снимаем комментарий со строки подключения роутера постов

```python
app.include_router(posts.router, prefix="/api/v1", tags=["posts"])
```

---

