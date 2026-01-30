### Простейший пример: Celery + RabbitMQ через Docker Compose

**Структура проекта**

```
celery-rabbitmq-example/
├── docker-compose.yml
├── requirements.txt
├── celery_app.py
├── tasks.py
└── test_script.py
```

**Устанавливаем пакеты** 
```bash
pip install celery[redis] flower

pip freeze > requirements.txt
```

**Запускаем RabbitMQ в контейнере:**

`docker-compose.yml`

```yaml
services:
  rabbitmq:
    image: rabbitmq:4-management  
    container_name: rabbitmq
    ports:
      - "5672:5672"     # AMQP для Celery
      - "15672:15672"   # веб-интерфейс (guest/guest)
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  rabbitmq-data:
```

**Основная конфигурация Celery**  
(брокер — RabbitMQ,  
backend — простой RPC через тот же RabbitMQ)

`celery_app.py`

```python
from celery import Celery

app = Celery(
    "rabbitmq_example",
    broker="amqp://guest:guest@localhost:5672//",  # ← на хосте используем localhost
    # Если воркер внутри docker-сети — замените на rabbitmq:5672
    # broker="amqp://guest:guest@rabbitmq:5672//",

    backend="rpc://",  # результаты возвращаются через RabbitMQ (просто для тестов)
    # Альтернатива: backend="redis://localhost:6379/0" — если добавить redis в compose

    include=["tasks"],
)

# Полезные настройки (почти без изменений)
app.conf.update(
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=29 * 60,
    result_expires=3600,  # результаты храним 1 час
    worker_concurrency=2,

    # Рекомендации для RabbitMQ в Docker
    broker_connection_retry_on_startup=True,
    broker_heartbeat=0,  # часто отключают в контейнерах
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
```

**Модуль с задачами:**

`tasks.py` (без изменений)

```python
from celery_app import app
import time

@app.task
def add(x, y):
    """Простая задача для теста"""
    time.sleep(3)  # имитируем долгую работу
    result = x + y
    print(f"Задача выполнена: {x} + {y} = {result}")
    return result

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def flaky_task(self):
    """Задача, которая иногда падает"""
    if time.time() % 2 > 1:  # ~50% шанс упасть
        raise ValueError("Ой, упал!")
    return "Всё ок!"
```

**Тестовый скрипт** (запускается на хосте, когда RabbitMQ уже работает)

`test_script.py` (без изменений)

```python
from celery_app import app
from tasks import add, flaky_task

if __name__ == "__main__":
    res1 = add.delay(7, 11)
    print("Задача add отправлена, id =", res1.id)

    # Для теста можно подождать результат (в продакшене лучше .get() избегать)
    print("Результат:", res1.get(timeout=10))

    # Цепочка задач
    chained = (add.s(100, 200) | add.s(300)).delay()
    print("Цепочка отправлена, id =", chained.id)

    # Задача с ретраями
    flaky_task.delay()
```

## Начинаем наши исследования

1. Запускаем RabbitMQ:

```bash
docker compose up --build
```

2. Открываем веб-интерфейс RabbitMQ (для проверки):

[http://localhost:15672](http://localhost:15672) → логин/пароль: **guest** / **guest**

Статистика отсутствует по вполне очевидным причинам. 

3. Запускаем Flower
```bash
celery -A celery_app flower --port=5555
```

[http://localhost:5555](http://localhost:5555)

Если мы заглянем во Flower, то ничего не увидим (по тем же очевидным причинам).

Но мониторинг RabbitMQ покажет неожиданную активность. Но почему?  

Потому что Flower сам по себе — это клиент Celery, который очень активно стучится в RabbitMQ, даже если воркеров нет.  
Celery-воркеры обычно держат 1–2 соединения на worker (или даже 1 с несколькими channels), а Flower — 8–15+.  
Поэтому, в нашем случае Flower проще будет отключить.

`Ctrl + C` в терминале запуска Flower.

Проверяем - активность исчезла.


4. Запускаем Celery-воркер:

```bash
celery -A celery_app worker --loglevel=INFO -E
```

Видим привычную картину:

```text
celery -A celery_app worker --loglevel=INFO -E
 
 -------------- celery@su-Aspire-A517-58M v5.6.2 (recovery)                                                                                                                                                                
--- ***** -----                                                                                                                                                                                                            
-- ******* ---- Linux-6.11.0-17-generic-x86_64-with-glibc2.39 2026-01-28 22:16:36                                                                                                                                          
- *** --- * ---                                                                                                                                                                                                            
- ** ---------- [config]                                                                                                                                                                                                   
- ** ---------- .> app:         rabbitmq_example:0x71e06ca88a70                                                                                                                                                            
- ** ---------- .> transport:   amqp://guest:**@localhost:5672//                                                                                                                                                           
- ** ---------- .> results:     rpc://                                                                                                                                                                                     
- *** --- * --- .> concurrency: 2 (prefork)                                                                                                                                                                                
-- ******* ---- .> task events: ON                                                                                                                                                                                         
--- ***** -----                                                                                                                                                                                                            
 -------------- [queues]                                                                                                                                                                                                   
                .> celery           exchange=celery(direct) key=celery                                                                                                                                                     
                                                                                                                                                                                                                           
                                                                                                                                                                                                                           
[tasks]
  . tasks.add
  . tasks.flaky_task

[2026-01-28 22:16:36,566: INFO/MainProcess] Connected to amqp://guest:**@127.0.0.1:5672//
[2026-01-28 22:16:36,574: INFO/MainProcess] mingle: searching for neighbors
[2026-01-28 22:16:37,599: INFO/MainProcess] mingle: all alone
[2026-01-28 22:16:37,630: INFO/MainProcess] celery@su-Aspire-A517-58M ready.
```

4. В другом терминале запустить тестовый скрипт:

```bash
python test_script.py
```

5. Анализ мониторинга RabbitMQ

#### 1. Connections (~ 5 подключений)

Обычно **один Celery-воркер** создаёт **3–5 AMQP-соединений** к RabbitMQ.

Типичное распределение:

| Кол-во каналов | Назначение                                                                 | Пример в вашем случае                  |
|----------------|----------------------------------------------------------------------------|----------------------------------------|
| 3 канала       | **Основное рабочее соединение** (consumer + publisher + control)          | 172.27.0.1:34460 (3 channels)          |
| 1 канал        | **Broadcast-канал** (pidbox) — для удалённого управления воркером         | Один из одиночных (например, 34464)    |
| 1 канал        | **Gossip / Mingling** — обмен информацией между воркерами (даже если один) | Один из idle-соединений                |
| 1–2 канала     | **Heartbeat / контроль соединения** + резервные                            | Остальные idle-подключения             |

- Самое активное — то, у которого **3 channels** (34460).  
  Оно потребляет задачи, публикует результаты, отвечает на inspect-запросы.
- Остальные — в основном **idle** (0 B/s или почти 0), они просто держатся открытыми для быстрого использования (heartbeat, gossip, control).

**Почему не 1 соединение?**  
Celery специально разделяет ответственность: 
* задачи, 
* контроль, 
* события — разные вещи, и kombu предпочитает отдельные соединения/каналы, чтобы не блокировать друг друга.
 

### 2. Channels (~ 7 каналов)

- **34460 (1)** — idle, prefetch=8 (global)
  - это основной consumer-канал, который ждёт задач 
  - (prefetch — сколько задач может взять "на грудь" заранее).
- **34460 (2)** — running, publish rate 0.40/s 
  - канал, через который воркер **отправляет** результаты задач, heartbeats, события.
- **34460 (3)** — idle 
  - → резервный / control.
- Остальные одиночные каналы — pidbox, gossip, heartbeat и т.д. (idle).

**Prefetch = 8 (global)** — это значение по умолчанию в Celery (worker_prefetch_multiplier=4 × concurrency).  
При `--concurrency=2` → 8 задач может быть взято заранее. 

### 3. Queues (3 очереди)

Это **стандартные очереди**, которые Celery создаёт автоматически:

| Имя очереди                                      | Назначение                                                                                                                                                                             | Почему TTL / Exp?                  |
|--------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| `celery`                                         | Основная очередь задач <br>(сюда приходят все `@app.task` без явного указания queue)                                                                                                   | —                                   |
| `celery@su-Aspire-A517-58M.celery.pidbox`        | **Pidbox** — очередь для **удалённого управления** воркером <br>(inspect, revoke, shutdown и т.д.)                                                                                     | Auto-delete + TTL (временная)      |
| `celeryev.66b9794d-6594-4c51-85ef-dd4b54105c49`  | **События** (events) — сюда публикуются все события воркера <br>(task-received, succeeded, failed, started и т.д.). <br>Нужно для Flower, Flower-совместимых мониторингов, dashboards. | Auto-delete + TTL (очень временная) |

- `celeryev.*` — уникальное имя для каждого воркера (содержит hostname + uuid).

