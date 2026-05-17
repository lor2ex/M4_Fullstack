### 1. Создаём задачу-оркестратор `pipeline`

1. Celery Beat не работает с обычным Python-скриптом. Он работает только с задачами.
2. Блокирующий `.get()` ему тоже не подходит. Поэтому меняем его на `group + chord`

`app/tasks/pipeline.py` 

```python
from celery import shared_task, group, chord, chain
from app.tasks.parse_sites import parse_site_task
from app.tasks.parse_tg import parse_tg_task
from app.tasks.filter import filter_posts_task
from app.tasks.generate import generate_post_task
from app.redis_sync import get_sync_redis


def get_all_source_names():
    redis = get_sync_redis()
    keys = redis.keys("site_sources:*")
    return [key.split(":")[1] for key in keys]


def get_all_tg_names():
    redis = get_sync_redis()
    keys = redis.keys("tg_sources:*")
    return [key.split(":")[1] for key in keys]


# --- Основная функция pipeline, теперь без .get() ---
def start_pipeline():
    source_site_names = get_all_source_names()
    source_tg_names = get_all_tg_names()

    if not (source_site_names or source_tg_names):
        print("Нет источников")
        return

    # --- 1. Парсинг ---
    parse_tasks = (
        [parse_site_task.s(source_name=name) for name in source_site_names] +
        [parse_tg_task.s(source_name=name) for name in source_tg_names]
    )

    if not parse_tasks:
        print("Нет задач для парсинга")
        return

    # --- 2. После парсинга → фильтрация → генерация ---
    workflow = chord(parse_tasks)(
        chain(
            filter_posts_task.s(),
            generate_all_posts.s()
        )
    )

    print("Pipeline запущен через Celery. Задачи идут асинхронно.")
    return workflow


# --- Callback для генерации постов ---
@shared_task
def generate_all_posts(_):
    redis = get_sync_redis()
    filtered_keys = redis.keys("news:filtered:*")

    if not filtered_keys:
        print("Нет отфильтрованных новостей для генерации")
        return 0

    print(f"Генерация запущена для {len(filtered_keys)} новостей")

    tasks = [
        generate_post_task.s(
            key.decode("utf-8") if isinstance(key, bytes) else key
        )
        for key in filtered_keys
    ]

    group(tasks).apply_async()
    return len(filtered_keys)


# --- Celery задача для Beat ---
@shared_task
def run_pipeline_task():
    start_pipeline()
```

### 2. Добавляем в `celery_app` новую задачу и настройки для Celery Beat

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'run-news-pipeline-every-hour': {
        'task': 'app.tasks.pipeline.run_news_pipeline',
        # 'schedule': crontab(minute=0, hour='*/30'),   # каждые 30 мин
        'schedule': crontab(minute='*/5')  # каждые 5 минут
    },
}

```


### 3. Запускаем Celery Beat

1. Перезапускаем Celery Worker

```bash
celery -A celery_app worker --pool=solo -l info
```

2. Запускаем Celery Beat 


```bash
celery -A celery_app beat -l info
```