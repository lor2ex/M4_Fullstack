## Запуск задач по расписанию

Ещё одно достоинство Celery — более удобный вариант замены `cron`

### 1. Добавляем 2 периодические задачи в предыдущий пример


### 1.1. Добавляем запуск по расписанию в `celery_app.py`

```python
# periodic.py

from celery.schedules import crontab

app.conf.beat_schedule = {
    'add-every-30-seconds': {
        'task': 'tasks.add',
        'schedule': 30.0,               # каждые 30 секунд
        'args': (6, 8)
    },
    'say-hello-every-2-minutes': {
        'task': 'tasks.hello',
        'schedule': crontab(minute='*/2'),
        'args': (),
    },
}
```

### 1.2. Добавляем новую задачу в файл `tasks.py`:

```python
@app.task
def hello():
    print("Привет! Я периодическая задача :)")
    return "Hello from beat"
```

### 2. Шаги по запуску:

- пере-запускаем воркер: `celery -A celery_app worker -l info -E`
- запускаем beat: `celery -A celery_app beat -l info`
- запускаем flower (если не был запущен до этого): `celery -A celery_app flower`

И смотрим логи в терминалах и во Flower.