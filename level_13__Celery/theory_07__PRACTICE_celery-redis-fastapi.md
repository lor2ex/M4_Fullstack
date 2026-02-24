## celery-redis-fastapi

### 1. Структура проекта

```
celery-redis-fastapi/
├── docker-compose.yml      # Конфигурация для запуска Redis через Docker
├── requirements.txt        # Список зависимостей для pip
├── main.py                 # Основной файл FastAPI-приложения с роутами
├── celery_app.py           # Конфигурация Celery приложения
└── tasks.py                # Определение Celery-задач
```

### 2. Зависимости для pip install

```bash
pip install fastapi[standard] celery[redis] uvicorn

pip freeze > requirements.txt
```

### 3. Файлы, которые необходимо добавить в проект:

**`docker-compose.yml`**

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

**`celery_app.py`**

```python
from celery import Celery

app = Celery(
    'celery_app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['tasks']
)

app.conf.update(
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json'
)
```

**`tasks.py`**

```python
from celery_app import app
import time

@app.task
def add(x, y):
    time.sleep(10)  # Небольшая задержка для демонстрации
    return x + y
```

**`main.py`**

```python
from fastapi import FastAPI
from celery.result import AsyncResult

from tasks import add

app = FastAPI()


@app.get("/run-task/")
async def run_task():
    """
    Плохой синхронный вариант для демонстрации
    """
    task = add.delay(4, 5)
    result = task.get(timeout=10.5)  # Ждём результат с таймаутом
    return {'task_id': task.id, 'result': result}


@app.get("/run-task-async/")
async def run_task_async():
    """
    Хороший асинхронный вариант для продакшн
    1. В этом эндпоинте мы только отправляем задачу на исполнение.
    2. А результат смотрим через http://127.0.0.1:8000/task-status/9a501c03-9a54-4399-a6c7-a37bb1baf534/
    ГЛАВНОЕ: не забыть взять из респонса id задачи!
    """
    task = add.delay(4, 5)
    return {'task_id': task.id, 'status': 'started'}


@app.get("/task-status/{task_id}")
async def task_status(task_id: str):
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

    return response
```

### 4. Шаги по запуску:

1. Запускаем Redis: `docker compose up`
2. В отдельном терминале запускаем воркер: `celery -A celery_app worker -l info`.
3. Запускаем сервер: `uvicorn main:app --reload`.
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
   * Однако здесь нет результата, есть только id новой АСИНХРОННОЙ задачи: `72e70c61-6e25-4d61-829d-c6cb30a30a31`
6. Чтобы увидеть результат, делаем новый запрос: `http://127.0.0.1:8000/task-status/task_id/`
   * Вместо `task_id` необходимо подставить id из предыдущего ответа: `http://127.0.0.1:8000/task-status/92e0a257-4061-41b1-8fe0-d4e6d9ecdcf4/`