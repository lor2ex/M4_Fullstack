## Асинхронная работа с очередями сообщений в FastAPI

Теперь рассмотрим пример работы очередей в FasAPI

#### 1. Обновлённая структура проекта

```
fastapi-rabbit-local/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   └── rabbit.py
├── .env
├── docker-compose.yaml
├── send_messages.py
├── requirements.txt
```

#### 2. Добавлеем `.env` 

```env
RABBITMQ_URL=amqp://guest:guest@localhost/
QUEUE_NAME=fastapi_local_queue
```


#### 3. Обновляем пакеты в `requirements.txt`

```bash
pip install fastapi uvicorn[standard] aio-pika python-dotenv requests

pip freeze > requirements.txt
```


#### 4. `app/config.py`

```python
from dotenv import load_dotenv
import os

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
QUEUE_NAME   = os.getenv("QUEUE_NAME",   "fastapi_local_queue")
```

#### 5. `app/rabbit.py` (центральная логика, robust + переподключение)

```python
import asyncio
import logging

import aio_pika
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractRobustConnection
from app.config import RABBITMQ_URL, QUEUE_NAME

logger = logging.getLogger(__name__)

_connection: AbstractRobustConnection | None = None


async def get_connection() -> AbstractRobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(RABBITMQ_URL)
        logger.info("Подключение к RabbitMQ установлено")
    return _connection


async def publish(message: str):
    conn = await get_connection()
    async with conn.channel() as ch:
        await ch.default_exchange.publish(
            Message(
                body=message.encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
            ),
            routing_key=QUEUE_NAME,
        )
    logger.info(f"Опубликовано: {message}")


async def consume_forever(process_func):
    """Простой consumer без while True — lifespan сам управляет"""
    conn = await get_connection()
    async with conn.channel() as ch:
        await ch.set_qos(prefetch_count=1)

        queue = await ch.declare_queue(
            QUEUE_NAME, 
            durable=True, 
            arguments={"x-queue-type": "classic"}
        )

        async def on_msg(msg: aio_pika.IncomingMessage):
            async with msg.process(requeue=True):
                body = msg.body.decode(errors="replace")
                logger.info(f"Получено: {body}")
                await process_func(body)

        await queue.consume(on_msg, no_ack=False)
        logger.info(f"Консьюмер запущен на очереди {QUEUE_NAME}")

        # Держим открытым до отмены задачи (lifespan отменит)
        await asyncio.sleep(float("inf"))  # или await conn.connected.wait()

```

##### 1. `delivery_mode=DeliveryMode.PERSISTENT`


```python
Message(
    body=message.encode(),
    delivery_mode=DeliveryMode.PERSISTENT,
)
```

- Сообщение будет **записано на диск** (persistent = устойчивый).
- Если RabbitMQ упадёт или перезапустится → это сообщение **не потеряется** (при условии, что очередь тоже durable).
- Без `PERSISTENT` (по умолчанию `DeliveryMode.TRANSIENT`) сообщение живёт только в памяти → при перезапуске 
  - брокера все такие сообщения пропадают.

> **Важный нюанс:**
> `delivery_mode=PERSISTENT` имеет смысл **только вместе с `durable=True` на очереди**.   
> Если очередь transient (не durable) → сообщение всё равно потеряется при перезапуске RabbitMQ, даже если оно persistent.

**Когда использовать:**
- Когда сообщение важно (заказ, платёж, уведомление пользователя, задание на обработку файла и т.д.).
- Когда потеря даже одного сообщения недопустима.

**Когда НЕ использовать:**
- Для лёгких, не критичных событий (логи, метрики, heartbeat, чат-сообщения в реальном времени)  
  -  там TRANSIENT + transient queue быстрее и меньше нагружает диск.

##### 2. `durable=True` в `declare_queue`

```python
queue = await ch.declare_queue(
    QUEUE_NAME, 
    durable=True,                          # ← здесь
    arguments={"x-queue-type": "classic"}
)
```
**Что это значит:**

- Очередь **сохраняется на диске** и **выживает после перезапуска RabbitMQ**.
- Даже если все потребители и продюсеры отключатся → очередь останется существовать с тем же именем и настройками.
- Сообщения, которые были в durable-очереди и имели `delivery_mode=PERSISTENT`, будут восстановлены после рестарта брокера.

**Без `durable=True` (по умолчанию `False`):**
- Очередь существует, только пока есть хотя бы один consumer или binding.
- При перезапуске RabbitMQ очередь и все сообщения в ней пропадают.

### Почему очередь создаётся именно в consumer-е, а не в producer-е?

Это **очень распространённый и рекомендуемый паттерн** в RabbitMQ-приложениях. Причины:

> Очередь создаёт тот, кто **в ней заинтересован больше всех** — потребитель.  
> Producer просто кидает письма в почтовый ящик — ему не важно, из какого материала ящик сделан.

**Когда producer всё-таки может создавать очередь:**

> - В административных скриптах, миграциях, при деплое (отдельный init-скрипт).
> - Если producer — единственный, кто пишет в эту очередь, а consumer'ов много и они динамические.
> - В очень простых прототипах, где producer и consumer — один и тот же процесс.


#### 6. `app/main.py` (с lifespan)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from app.rabbit import publish, consume_forever, get_connection
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FastAPI + RabbitMQ (упрощённо)")


async def example_processor(body: str):
    logger.info(f"Обработка: {body}")
    await asyncio.sleep(5.0)  # имитация
    logger.info(f"Обработано: {body}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    conn = await get_connection()  # инициализируем подключение заранее
    consumer_task = asyncio.create_task(consume_forever(example_processor))
    logger.info("FastAPI запущен, consumer запущен")

    yield

    # shutdown — graceful
    logger.info("Shutdown: отменяем consumer...")
    consumer_task.cancel()
    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
        logger.info("Consumer gracefully завершён")
    except asyncio.TimeoutError:
        logger.warning("Consumer не завершился за 5 сек — forceful cancel")
    except asyncio.CancelledError:
        pass

    # Закрываем глобальное подключение
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
        logger.info("RabbitMQ соединение закрыто")


app.router.lifespan_context = lifespan


class Message(BaseModel):
    content: str


@app.post("/send/")
async def send_to_queue(msg: Message, background_tasks: BackgroundTasks):
    background_tasks.add_task(publish, msg.content)
    return {"status": "Сообщение отправлено"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

```

#### 7. `send_messages.py` (отправка сообщений через http://localhost:8000/send/)

```python
import requests
import time
import random

# Настройки — подставь свой адрес FastAPI, если порт другой
BASE_URL = "http://127.0.0.1:8000"
ENDPOINT_SEND = "/send/"
ENDPOINT_HEALTH = "/health"

def check_health():
    """Проверяем, что FastAPI живой"""
    try:
        response = requests.get(f"{BASE_URL}{ENDPOINT_HEALTH}")
        if response.status_code == 200:
            print("FastAPI работает нормально:", response.json())
            return True
        else:
            print(f"Ошибка health-check: {response.status_code} - {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Не удалось подключиться к FastAPI: {e}")
        return False


def send_message(content: str):
    """Отправляем одно сообщение в очередь"""
    payload = {"content": content}

    try:
        response = requests.post(
            f"{BASE_URL}{ENDPOINT_SEND}",
            json=payload,  # автоматически сериализует в JSON
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"Успешно отправлено: {content!r} → {response.json()}")
        else:
            print(f"Ошибка отправки: {response.status_code} - {response.text}")
    except requests.RequestException as e:
        print(f"Ошибка при запросе: {e}")


def main():
    if not check_health():
        print("Прерываем — сервер недоступен")
        return

    print("\nОтправляем тестовые сообщения...\n")

    messages = [
        "Привет из requests-скрипта! №1",
        "Тестовое задание 2026",
        "Проверить интеграцию FastAPI + RabbitMQ",
        "Сообщение с эмодзи: 🚀🐇",
        "Последнее сообщение для теста"
    ]

    for msg in messages * 10:
        send_message(msg)
        # небольшая пауза, чтобы увидеть динамику в UI RabbitMQ
        time.sleep(random.uniform(0.5, 1))

    print("\nВсе сообщения отправлены. Проверь консоль FastAPI и RabbitMQ UI.")


if __name__ == "__main__":
    main()

```


### Запуск

1. Запускаем контейнер (или проверяем, что запущен)

   ```bash
   docker compose up -d
   # или docker-compose up -d (в зависимости от версии docker)
   ```

2. Проверяем UI: http://localhost:15672 → guest/guest → Queues (пока пусто)

3. Запускаем FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

4. Запускаем скрипт `sand_messages.py`

Этот скрипт отправляет сообщения на FastAPI через RabbitMQ

Можем наблюдать изменение параметров Queue в [http://localhost:15672/#/queues](http://localhost:15672/#/queues),
регулируя соотношение время отправки ко времени обработки:

**время отправки**
```python
    for msg in messages * 10:
        send_message(msg)
        # небольшая пауза, чтобы увидеть динамику в UI RabbitMQ
        time.sleep(random.uniform(0.5, 1))
```

**время обработки**
```python
async def example_processor(body: str):
    logger.info(f"Обработка: {body}")
    await asyncio.sleep(5.0)  # имитация
    logger.info(f"Обработано: {body}")
```

