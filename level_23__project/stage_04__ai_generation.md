### AI-генерация постов

Если возникает ошибка 429, код будет перезапущен через 30 секунд.  
И так 3 раза.

⚠️ На забудьте проверить актуальные ключ `AI_API_KEY` в `local_settings.py`

`app/ai/generator.py`

```python
import time
import httpx
from app.config import settings
from app.schemas.generate import GenerateResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

FREE_AI_URL = "https://apifreellm.com/api/v1/chat"


def ai_generate_post(title: str, summary: str, max_retries: int = 3) -> GenerateResponse:
    """
    Возвращает (новый_заголовок, сгенерированный_пост)
    """
    if not title or not summary:
        raise ValueError("Title и summary обязательны")

    prompt = (
        f"Сделай яркий, лаконичный и интересный пост для Telegram-канала на основе новости.\n"
        f"Заголовок новости: {title}\n"
        f"Краткое содержание: {summary}\n\n"
        "Требования:\n"
        "• 5-7 предложений максимум\n"
        "• Добавь 2–4 релевантных emoji\n"
        "• Стиль живой, как у хорошего Telegram-канала\n"
        "• Не используй слова «дорогие друзья» и «новость дня»\n"
        'В ответе отделе новый заголовок от текста тройным символом |||'
    )

    payload = {"message": prompt}

    attempt = 0

    while attempt <= max_retries:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    FREE_AI_URL,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.ai_api_key}",
                    },
                )
                response.raise_for_status()
                data = response.json()

                generated_text = data.get("response") or data.get("text") or str(data)

                lines = generated_text.strip().split("|||", 1)
                new_title = lines[0].strip("# *").strip() if lines else title
                post_text = lines[1].strip() if len(lines) > 1 else generated_text

                logger.info(f"AI успешно сгенерировал пост для: {title[:50]}...")

                return GenerateResponse(
                    original_title=title,
                    new_title=new_title,
                    generated_post=post_text,
                )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code

            if status_code == 429 and attempt < max_retries:
                attempt += 1
                logger.warning(
                    f"Получен 429 (rate limit). Попытка {attempt}/{max_retries}. "
                    "Повтор через 30 секунд..."
                )
                time.sleep(30)
                logger.warning(f"Попытка #{attempt+1}: запуск...")
                continue

            logger.error(f"AI API error {status_code}: {e.response.text}")
            raise

        except Exception:
            logger.exception("Неизвестная ошибка при генерации AI")
            raise

    raise RuntimeError("Превышено максимальное количество попыток при 429")


if __name__ == "__main__":
    params = {
      "title": "Фреймворк FastAPI выходит на лидирующие позиции",
      "summary": "Фреймворк FastAPI стремительно выходит на лидирующие позиции среди инструментов для разработки веб-приложений на Python."
    }
    print(ai_generate_post(**params))

```

**Проводим smoke тест (только сначала выполним следующий пункт!)**


### 2. Эндпойнт для ручной AI генерации 

`app/schemas/generate.py`

```python
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=300)
    summary: str = Field(..., min_length=10, max_length=2000)

class GenerateResponse(BaseModel):
    original_title: str
    new_title: str
    generated_post: str
```

`app/api/v1/generate.py`

```python
from fastapi import APIRouter, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.schemas.generate import GenerateRequest, GenerateResponse
from app.ai.generator import ai_generate_post
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/", response_model=GenerateResponse, status_code=200)
async def manual_generate(request: GenerateRequest):
    """
    Ручная генерация поста через AI (для тестов и отладки)
    """
    logger.info(f"Ручная генерация запрошена: {request.title[:80]}...")

    try:
        result: GenerateResponse = await run_in_threadpool(
            ai_generate_post,
            request.title,
            request.summary,
        )

        return result


    except Exception as e:
        logger.exception("Ошибка ручной генерации")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}",
        )

```

Раскомменчиваем роутер

```python
app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
```

### 3. Делаем пробную генерацию

```
{
  "title": "Фреймворк FastAPI выходит на лидирующие позиции",
  "summary": "Фреймворк FastAPI стремительно выходит на лидирующие позиции среди инструментов для разработки веб-приложений на Python."
}
```

### 4. Задача AI генерации 

`app/tasks/generate.py`

```python
import hashlib
from datetime import datetime
from celery import shared_task

from app.ai.generator import ai_generate_post
from app.redis_sync import get_sync_redis
from app.schemas.generate import GenerateResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

GENERATED_TTL = 24 * 60 * 60
GENERATED_PREFIX = "news:generated"


def _decode_redis_hash(raw_data: dict) -> dict:
    """Помощник: декодирует bytes → str (redis-py по умолчанию отдаёт bytes)"""
    decoded = {}
    for k, v in raw_data.items():
        key = k.decode("utf-8") if isinstance(k, bytes) else k
        value = v.decode("utf-8") if isinstance(v, bytes) else v
        decoded[key] = value
    return decoded


@shared_task(bind=True, name="generate_post", max_retries=2)
def generate_post_task(self, filtered_key: str):
    """
    Генерация AI-поста.
    Всегда возвращает int: 1 = успех, 0 = провал (чтобы sum() в pipeline не падал).
    """
    redis = get_sync_redis()

    try:
        raw_data = redis.hgetall(filtered_key)
        if not raw_data:
            logger.warning(f"Отфильтрованная новость не найдена: {filtered_key}")
            return 0

        data = _decode_redis_hash(raw_data)

        title = data.get("title", "")
        summary = data.get("summary", "")
        source = data.get("source", "unknown")
        published_at_str = data.get("published_at", "")

        if not title or not summary:
            logger.error(f"Недостаточно данных для генерации: {filtered_key}")
            return 0

        logger.info(f"Генерация поста для [{source}] → {title[:70]}...")

        response: GenerateResponse = ai_generate_post(title, summary)

        content_hash = hashlib.md5(
            f"{title}{summary}{published_at_str}".encode()
        ).hexdigest()[:16]

        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

        redis.hset(
            generated_key,
            mapping={
                "original_title": response.original_title,
                "new_title": response.new_title,
                "generated_post": response.generated_post,
                "hash": content_hash,
                "source": source,
                "generated_at": datetime.now().isoformat(),
            },
        )
        redis.expire(generated_key, GENERATED_TTL)

        logger.info(f"Сгенерированный пост сохранён → {generated_key}")
        return 1

    except Exception as e:
        logger.exception(f"Ошибка генерации поста для {filtered_key}")
        raise self.retry(exc=e, countdown=60)

```

----

### 5. Добавляем задачу в `celery_app.py`


```python
include = [
    "app.tasks.parse_sites",
    "app.tasks.filter",
    "app.tasks.generate",  # новая задача
]
```

----

### 6. Добавляем запуск задачи в `run_pipeline.py`

```python
from app.tasks.generate import generate_post_task




...

    # --- Запуск генерации постов -------------------------------------

    redis = get_sync_redis()
    filtered_keys = redis.keys("news:filtered:*")

    if not filtered_keys:
        print("Нет отфильтрованных новостей для генерации")
    else:
        print(f"Найдено отфильтрованных новостей: {len(filtered_keys)}")
        generate_group = group(
            generate_post_task.s(
                key.decode("utf-8") if isinstance(key, bytes) else key
            )
            for key in filtered_keys
        )

        try:
            gen_counts = generate_group.apply_async().get(timeout=600)
            total_generated = sum(x or 0 for x in gen_counts)
            print(f"Генерация завершена. Успешно сгенерировано: {total_generated}")
        except Exception as e:
            print(f"Ошибка при генерации: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

```

----

### 7. Добавляем схему и эндпойнт отображения сгенерированных новостей 

#### 7.1. `app/schemas/generate.py`

```python

...

class GeneratedPostOut(GenerateResponse):
    key: str = Field(..., description="Redis-ключ записи")
    hash: str = Field(..., description="MD5 хеш оригинала")
```


#### 7.2. Замените импорты

`app/api/v1/generate.py`

```python
from fastapi import APIRouter, HTTPException, status, Query, Depends
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_redis
from app.schemas.generate import GenerateRequest, GenerateResponse, GeneratedPostOut
from app.ai.generator import ai_generate_post
from app.utils.logging import get_logger

GENERATED_PREFIX = "news:generated"

```

#### 7.3. И добавьте новый эндпойнт

`app/api/v1/generate.py`

```python
@router.get("/", response_model=list[GeneratedPostOut])
async def list_generated_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    redis=Depends(get_redis),
):
    try:
        raw_keys = await redis.keys(f"{GENERATED_PREFIX}:*")
        keys = [k.decode("utf-8") if isinstance(k, bytes) else k for k in raw_keys]
        keys.sort(reverse=True)  # новые сверху

        if not keys:
            return []

        paginated_keys = keys[skip : skip + limit]

        result = []
        for key in paginated_keys:
            data = await redis.hgetall(key)
            if not data:
                continue

            result.append(
                GeneratedPostOut(
                    key=key,
                    original_title=data.get("original_title"),
                    new_title=data.get("new_title"),
                    generated_post=data.get("generated_post"),
                    hash=data.get("hash"),
                )
            )

        return result

    except Exception as e:
        logger.exception("Ошибка получения сгенерированных постов")
        raise HTTPException(status_code=500, detail="Не удалось получить список")
    
```

### 8. Перезапускаем воркер и проверяем работу ОП

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
Результаты: [0, 0, 0, 0]
Всего сохранено: 0
Фильтрация запущена. Ждём результата...
Отфильтровано: 0
Найдено отфильтрованных новостей: 4
Генерация завершена. Успешно сгенерировано: 4

```

И просматриваем результаты в двух новых эндпойнтах

### 9.* вариант для `production`

`run_pipeline.py`*

```python
from celery import group, chord

from celery_app import celery_app
from app.tasks.parse_sites import parse_site_task
from app.tasks.filter import filter_posts_task
from app.redis_sync import get_sync_redis
from app.tasks.generate import generate_post_task


def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [
        key.split(":")[1]
        for key in keys
    ]


@celery_app.task
def start_generation(_):
    """
    Callback после фильтрации.
    Запускает генерацию постов по всем отфильтрованным новостям.
    
    start_generation.s() требует наличие хотя бы одного аргумента.
    Поэтому передаём символ подчёркивания "_"
    
    return result.id - возвращаем id группы, где каждая из задач
    запускается асинхронно

    """

    # --- Запуск генерации постов -------------------------------------

    redis = get_sync_redis()
    filtered_keys = redis.keys("news:filtered:*")

    if not filtered_keys:
        print("Нет отфильтрованных новостей для генерации")
        return 0

    print(f"Найдено отфильтрованных новостей: {len(filtered_keys)}")

    generate_group = group(
        generate_post_task.s(
            key.decode("utf-8") if isinstance(key, bytes) else key
        )
        for key in filtered_keys
    )

    result = generate_group.apply_async()

    print("Генерация постов запущена")

    return result.id


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

    print("Задачи запущены (parse -> filter -> generate)...")

    # --- После завершения парсинга запускается фильтрация,
    # --- затем генерация постов --------------------------------------

    workflow = chord(parse_group)(
        filter_posts_task.si() | start_generation.s()
    )

    print(f"Workflow запущен: {workflow.id}")


if __name__ == "__main__":
    main()
```