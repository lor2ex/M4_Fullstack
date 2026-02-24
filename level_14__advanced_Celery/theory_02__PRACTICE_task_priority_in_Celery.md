❗ Важное замечание:  
**Celery НЕ поддерживает приоритеты задач!**  
**Celery ТОЛЬКО передаёт `priority` в брокер.**

Исследуем, как Celery реализует приоритеты задач в обоих случаях:
* и когда в качестве брокеров использует RabbitMQ 
* и когда использует Radis

---



### 1. Структура Python-проекта
```
celery_priority_demo/
├── docker-compose.yml
├── celery_app.py
├── requirements.txt
├── tasks.py
├── send_priority_tasks.py
├── send_queue_tasks.py
```

Один проект — разные сценарии:
* `send_priority_tasks.py` - тестирует работу с брокером Rabbit
* `send_queue_tasks.py` - тестирует работу с брокером Radis


#### Устанавливаем зависимости:

```bash
pip install celery[redis,librabbitmq] gevent

pip freeze > requirements.txt
```

---

### 2. Docker Compose: RabbitMQ + Redis

Создаём `docker-compose.yml`:

```yaml
services:
  rabbitmq:
    image: rabbitmq:3.12-management
    container_name: rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

  redis:
    image: redis:7
    container_name: redis
    ports:
      - "6379:6379"
```

---

### 3. Celery app: очереди + priority (универсальная конфигурация)

## `celery_app.py`

```python
from celery import Celery
from kombu import Queue

BROKER = "amqp://guest:guest@localhost:5672//"
# BROKER = "redis://localhost:6379/0"

app = Celery(
    "priority_demo",
    broker=BROKER,
    backend="redis://localhost:6379/1",
    include=["tasks"],
)

app.conf.update(
    # ===== Очереди =====
    task_queues=(
        # Для RabbitMQ priority
        Queue(
            "priority",
            routing_key="priority",
            queue_arguments={
                "x-max-priority": 10,
            },
        ),

        # Для Redis-приоритетов через очереди
        Queue("high"),
        Queue("default"),
        Queue("low"),
    ),

    task_default_queue="default",

    # ===== КРИТИЧНО для демонстрации =====
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    task_serializer="json",
    accept_content=["json"],
    worker_concurrency=1,   # Чтобы задачи шли строго последовательно
)
```


* **RabbitMQ** использует очередь `priority`
* **Redis** использует очереди `high → default → low`

---

### 4. Задача

#### `tasks.py`

```python
import time
from celery_app import app


@app.task
def demo_task(name, duration=2):
    print(f"START {name}")
    time.sleep(duration)
    print(f"END   {name}")
```

---

### 5. Сценарий 1 — RabbitMQ + priority

#### Broker

```python
BROKER = "amqp://guest:guest@localhost:5672//"
```

#### Worker

```bash
celery -A celery_app worker -Q priority -l INFO
```

#### Отправка

**`send_priority_tasks.py`**

```python
from tasks import demo_task

tasks = [
    ("low-1", 1),
    ("low-2", 1),
    ("high-1", 9),
    ("medium-1", 5),
    ("high-2", 9),
]

for name, priority in tasks:
    demo_task.apply_async(
        args=(name, 5),
        queue="priority",
        priority=priority,
    )
    print(f"Sent {name} priority={priority}")
```

#### Результат 

```
low-1   
low-2
high-1
medium-1
high-2
```

Как видим, полное фиаско. Почему?  
Потому что в приоритетах настроек воркера параметры потоков и захватов задач в настройках конфигурации самые низкие.  
И он может не обратить внимание на эти настройки, если в системной переменной число ядер будет > 2.  

Поэтому для задач с приоритетами лучше указывать эти параметры прямо в командной строке:

```bash
celery -A celery_app worker -Q priority -l INFO --concurrency=1 --prefetch-multiplier=1
```

#### Останавливаем воркер и запускаем с новыми параметрами

```
low-1   
high-1
high-2
medium-1
low-2
```

Первая задача всё равно проскочит (потому что одна в очереди)

Но все остальные выстроятся в правильном порядке

---

### 6. Сценарий 2 — Redis + priority (НЕ работает)

#### Broker

```python
BROKER = "redis://localhost:6379/0"
```

Worker и sender — **без изменений**.

#### Результат

```
low-1   
low-2
high-1
medium-1
high-2
```

Priority **полностью игнорируется**.

---

### 7. Сценарий 3 — Redis + очереди (рабочий приоритет)

#### Отправка по очередям

**`send_queue_tasks.py`**

```python
from tasks import demo_task

demo_task.apply_async(args=("low-1",), queue="low")
demo_task.apply_async(args=("low-2",), queue="low")
demo_task.apply_async(args=("default-1",), queue="default")
demo_task.apply_async(args=("high-1",), queue="high")
demo_task.apply_async(args=("high-2",), queue="high")
```

#### Worker

Запускаем 3 воркера в 3-х терминалах

```bash
celery -A celery_app worker -Q high -l INFO  --concurrency=1 --prefetch-multiplier=1
```

```bash
celery -A celery_app worker -Q default -l INFO  --concurrency=1 --prefetch-multiplier=1
```

```bash
celery -A celery_app worker -Q low -l INFO  --concurrency=1 --prefetch-multiplier=1
```
#### Результат

В каждом воркере будет обработана "своя" задача.

Это **не priority**, а **детерминированный порядок чтения очередей**.

---

### 8. Что именно мы доказали

1. Celery не сортирует задачи  
2. Priority реализует брокер 
3. Redis priority — фикция 
4. Redis + очереди — рабочая модель 
5. Prefetch ломает приоритеты 

---

### 9. Принцип работы RabbitMQ и Redis

```
RabbitMQ:
  queue(priority) → сортировка → worker

Redis:
  FIFO → worker
```

`RabbitMQ` - реальная сортировка задач по приоритету

`Redis` - сортировку не поддерживает, поэтому явно указываем имя очереди для соответствующей задачи.