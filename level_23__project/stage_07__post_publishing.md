## Генерация постов в телеграм

У нас остался один важные нерешённый вопрос: 
* "Как передать в задачу публикацию информацию о неопубликованных постах?"

Вероятно, самым простым решением будет добавить два новых поля в сгенерированные посты:

### 1. Изменяем модель сгенерированных постов

Добавляем два новых поля в модель `GeneratedPostOut`:
* `is_published` - опубликовано ли
* `published_at` - дата публикации

`app/schemas/generate.py`

```python
class GeneratedPostOut(GenerateResponse):
    key: str = Field(..., description="Redis-ключ записи")
    hash: str = Field(..., description="MD5 хеш оригинала")
    is_published: bool = False
    published_at: str | None = None
```

### 2. Добавляем задачу публикации

`app/tasks/publish.py`

```python
import time
from celery import shared_task

from app.telegram.publisher import post_to_channel
from app.redis_sync import get_sync_redis
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _decode_hash(data: dict) -> dict:
    """Декодирует bytes-ключи и значения из redis hgetall"""
    if not data:
        return {}
    return {
        (k.decode("utf-8") if isinstance(k, bytes) else k):
        (v.decode("utf-8") if isinstance(v, bytes) else v)
        for k, v in data.items()
    }


@shared_task(bind=True, max_retries=3, name="publish_to_telegram")
def publish_to_telegram_task(self, generated_key: str):
    redis = get_sync_redis()

    try:
        raw_data = redis.hgetall(generated_key)
        if not raw_data:
            logger.error(f"Сгенерированный пост не найден: {generated_key}")
            return 0

        data = _decode_hash(raw_data)

        # Проверяем, не опубликован ли уже
        if data.get("is_published") in ("1", "true"):
            logger.info(f"Пост уже опубликован ранее, пропускаем: {generated_key}")
            return 0

        title = data.get("new_title") or data.get("original_title") or "Без заголовка"
        text = data.get("generated_post", "")

        if not text:
            logger.warning(f"Пустой текст поста для ключа {generated_key}")
            return 0

        logger.info(f"Публикация в Telegram: {title[:80]}...")

        post_to_channel(title=title, text=text)

        # Отмечаем как опубликованный
        redis.hset(generated_key, mapping={
            "is_published": "1",
            "published_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        logger.info(f"Пост успешно опубликован → {generated_key}")
        return 1

    except Exception as e:
        logger.exception(f"Ошибка публикации поста {generated_key}")
        raise self.retry(exc=e, countdown=30)
```


### 3. Добавляем задачу в `selery_app.py`

```python
    include=[
        "app.tasks.parse_sites",
        "app.tasks.parse_tg",
        "app.tasks.filter",
        "app.tasks.generate",
        "app.tasks.publish"
    ],

```
### 4. Изменяем `run_pipeline.py`

1. Добавляем импорт

```python
from app.tasks.publish import publish_to_telegram_task
```

2. Добавляем блок обработки задачи публикации

```python
    # --- Запуск публикации в Telegram --------------------------------
    
    print("Запуск публикации в Telegram...")

    redis = get_sync_redis()
    generated_keys = redis.keys("news:generated:*")

    if not generated_keys:
        print("Нет сгенерированных постов для публикации")
    else:
        unpublished_keys = []
        for raw_key in generated_keys:
            key_str = raw_key.decode("utf-8") if isinstance(raw_key, bytes) else raw_key

            data = redis.hgetall(raw_key)  # data содержит bytes

            published_flag = data.get(b"is_published") or data.get("is_published")
            if published_flag is None:
                is_published = False
            else:
                flag_str = str(published_flag).strip().lower()
                is_published = flag_str in ("1", "true", "yes")

            if not is_published:
                unpublished_keys.append(key_str)

        if not unpublished_keys:
            print("Все сгенерированные посты уже опубликованы ранее.")
        else:
            print(f"Найдено неопубликованных постов: {len(unpublished_keys)}")

            publish_group = group(
                publish_to_telegram_task.s(key)
                for key in unpublished_keys
            )

            try:
                publish_results = publish_group.apply_async().get(timeout=300)
                total_published = sum(x or 0 for x in publish_results)
                print(f"Публикация завершена. Успешно опубликовано: {total_published} постов")
            except Exception as e:
                print(f"Ошибка при публикации: {type(e).__name__}: {e}")


```

### 5. Изменяем эндпойнт сгенерированных постов

Добавляем обработку двух новых полей в сгенерированных постах.

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
                    is_published=str(data.get("is_published")).lower() in ("1", "true"),
                    published_at=data.get("published_at"),
                )
            )

        return result

    except Exception as e:
        logger.exception("Ошибка получения сгенерированных постов")
        raise HTTPException(status_code=500, detail="Не удалось получить список")
```

### 6. Проверяем добавленный блок публикации в действии

```bash
celery -A celery_app worker --pool=solo -l info
```

```bash
python run_pipeline.py
```