## celery-redis-django

### 1. Структура проекта

```
celery-redis-django/
├── docker-compose.yml      # Конфигурация для запуска Redis через Docker
├── requirements.txt        # Список зависимостей для pip
├── manage.py               # Утилита управления Django
└── main/                   # Основная папка Django-проекта
    ├── __init__.py         # Инициализация пакета, с импортом Celery
    ├── settings.py         # Настройки Django, включая конфигурацию Celery
    ├── urls.py             # URL-роутинг проекта
    ├── celery.py           # Конфигурация Celery приложения
    ├── tasks.py            # Определение Celery-задач
    └── views.py            # Views для запуска задач
```


### 2. Зависимости для pip install

```bash
pip install Django celery[redis]

pip freeze > requirements.txt
```

### 3. Создаём Django-проект

В корне проекта выполняем команду:
```bash
django-admin startproject main .
```



### 4. Файлы, которые необходимо добавить в проект (дополнить / заменить):


**`docker-compose.yml`**

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**`main/settings.py`**

Добавляем настройки Celery / Radis в конец файла:

```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```


**`main/celery.py`**

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('main')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**`main/__init__.py`**

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**`main/tasks.py`**

```python
from celery import shared_task
import time

@shared_task
def add(x, y):
    time.sleep(10)  # Небольшая задержка для демонстрации
    return x + y
```

**`main/views.py`**

```python
from django.http import JsonResponse
from celery.result import AsyncResult

from .tasks import add


def run_task(request):
    """
    Плохой синхронный вариант для демонстрации
    """
    task = add.delay(4, 5)
    result = task.get(timeout=10.5)  # Ждём результат с таймаутом
    return JsonResponse({'task_id': task.id, 'result': result})


def run_task_async(request):
    """
    Хороший асинхронный вариант для продакшн
    1. В этом вью мы только отправляем задачу на исполнение.
    2. А результат смотрим через http://127.0.0.1:8000/task-status/9a501c03-9a54-4399-a6c7-a37bb1baf534/
    ГЛАВНОЕ: не забыть взять из респонса id задачи!
    """
    task = add.delay(4, 5)
    return JsonResponse({'task_id': task.id, 'status': 'started'})


def task_status(request, task_id):
    """
    Получаем статус задачи после её реального выполнения.
    ГЛАВНОЕ: не забыть взять из респонса id задачи!
    """
    result = AsyncResult(task_id)

    response = {
        'task_id': task_id,
        'status': result.status,
    }

    if result.ready():
        response['result'] = result.result

    return JsonResponse(response)
```

**`main/urls.py`**

```python
from django.contrib import admin
from django.urls import path
from .views import run_task, run_task_async, task_status

urlpatterns = [
    path('admin/', admin.site.urls),
    path('run-task/', run_task),
    path('run-task-async/', run_task_async),
    path('task-status/<str:task_id>/', task_status),
]

```


### 4. Шаги по запуску:

1. Запускаем Redis: `docker compose up`
2. В отдельном терминале запускаем воркер: `celery -A main worker -l info`.
3. Запустите сервер: `python manage.py runserver`.
4. Запускаем выполнение задачи синхронно `http://127.0.0.1:8000/run-task/`:
   * Через 10 сек ожидания видим JSON
   ```json
    {
        "task_id": "2e9faeaa-b393-47b6-913a-2f489a680b73", 
        "result": 9
    }
    ```
5. Даём команду на асинхронное исполнение задачи `http://127.0.0.1:8000/run-task-async/`:
   * Ответ на этот раз приходит мгновенно:
   ```json
    {
       "task_id": "72e70c61-6e25-4d61-829d-c6cb30a30a31", 
       "status": "started"
   }
    ```
   * Однако здесь нет результат, есть только id новой АСИНХРОННОЙ задачи: `72e70c61-6e25-4d61-829d-c6cb30a30a31`
6. Чтобы увидеть результат делаем новый запрос: 'http://127.0.0.1:8000/task-status/task_id/'
   * Вместо `task_id` необходимо подставить id из предыдущего ответа: 'http://127.0.0.1:8000/task-status/72e70c61-6e25-4d61-829d-c6cb30a30a31/'



