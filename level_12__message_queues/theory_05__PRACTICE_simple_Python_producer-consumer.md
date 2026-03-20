### Подключению Python producer-consumer кода к Docker-контейнеру с RabbitMQ

#### Шаг 1: Устанавливаем пакет `pika`

```bash
pip install pika
```

#### Шаг 2: Адаптация кода для RabbitMQ

- Для обмена сообщениями используем очередь RabbitMQ: 
  - producer публикует в exchange/queue, 
  - consumer подписывается.
- Создадим простую очередь (durable=False для теста).
- Сигнал завершения: 
  - Отправим специальное сообщение (например, 'STOP').
- Множественные producers/consumers работают асинхронно: 
  - `pika` поддерживает `threading.`

```python
import pika
import threading
import time
import random

# Параметры подключения (адаптируйте, если не дефолт)
RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = 'guest'
RABBITMQ_PASSWORD = 'guest'
QUEUE_NAME = 'my_queue'  # имя очереди

def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
    return pika.BlockingConnection(pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials
    ))

# ── ПРОИЗВОДИТЕЛЬ ────────────────────────────────
def producer(name):
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)  # создаём очередь, если нет

    for i in range(1, 11):
        item = f"{name} → {i:02d}"
        channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=item)
        print(f"  {item:18}  (отправлено)")
        time.sleep(4.0)

    # сигнал завершения для всех consumers
    channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body='STOP')
    connection.close()

# ── ПОТРЕБИТЕЛЬ ──────────────────────────────────
def consumer(name, stop_event):
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)

    def callback(ch, method, properties, body):
        item = body.decode()
        if item == 'STOP':
            print(f"{name}: Получен сигнал STOP")
            stop_event.set()  # сигнал для завершения
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"                     ← {item:18}")
        time.sleep(5.0)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # подтверждаем обработку

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    print(f"{name}: Запущен, жду сообщений...")
    channel.start_consuming()

# ── ЗАПУСК ───────────────────────────────────────
if __name__ == "__main__":
    # Для graceful shutdown consumers
    stop_events = []

    producers = []
    for i in range(2):
        t = threading.Thread(target=producer, args=(f"P{i+1}",))
        producers.append(t)
        t.start()

    consumers = []
    for i in range(3):
        stop_event = threading.Event()
        stop_events.append(stop_event)
        t = threading.Thread(target=consumer, args=(f"C{i+1}", stop_event), daemon=True)
        consumers.append(t)
        t.start()

    # Ждём завершения producers
    for p in producers:
        p.join()

    # Ждём, пока consumers обработают всё (через STOP)
    for stop_event in stop_events:
        stop_event.wait()  # ждём сигнала от каждого consumer

```


#### Шаг 3: Запуск и проверка

1. **Запускаем RabbitMQ контейнер**:
   
2. **Запускаем Python-код локально**:

3. **Проверяем в RabbitMQ UI** (http://localhost:15672/):
   - Логин: guest/guest.
   - На вкладке **Queues** 'my_queue' будет выглядеть примерно так: 
     - растёт/падает кол-во сообщений, publish/deliver rates.
     
| Virtual host | Name      | Type    | Features | State   | Ready | Unacked | Total | incoming | deliver / get | ack    |
|--------------|-----------|--------|---------|--------|-------|---------|-------|----------|---------------|--------|
| /            | my_queue  | classic | Args    | running | 0     | 2       | 2     | 0.40/s   | 0.40/s        | 0.40/s |

    - Unacked 2 (число сообщений, которые доставления потребителю, но ещё не подтверждены)
    - incoming 0.40/s (сколько сообщений проходит в секунду (как км/ч))



  - На вкладке **Connections** — примерно так:

| Name             | Username  | State   | SSL / TLS | Protocol   | Channels | From client | To client |  
|------------------|-----------|---------|-----------|------------|----------|-------------|-----------|
| 172.26.0.1:42498 | guest     | running | ○         | AMQP 0-9-1 | 1        | 0 B/s       | 0 B/s     |
| 172.26.0.1:42512 | guest     | running | ○         | AMQP 0-9-1 | 1        | 0 B/s       | 0 B/s     |
| 172.26.0.1:42550 | guest     | running | ○         | AMQP 0-9-1 | 1        | 0 B/s       | 0 B/s     |


#### Анализ работы 

Если время обработки сообщения потребителем выше, чем отправителем, то число соединений 
* сначала увеличится до 5 (3 получателей + 2 отправителя)
* число запущенных (`running`) соединений тоже достигнет пяти
* и далее, по мере обработки сообщений из очереди
  * число соединений уменьшится до 3-х (только каналы получателей)
  * и их состояние станет `idle` (холостой / незанятый)

* Если задержку потребителя сделать <= задержки отправителя 
  * (вместо `time.sleep(5.0)` сделать `time.sleep(0.5)`),
  * то таблица соединений мало изменится (только сократится общее время работы)
  * но изменится состояние очереди:
    * больше не будет неподтверждённых сообщений

     
| Virtual host | Name      | Type    | Features | State   | Ready | Unacked | Total | incoming | deliver / get | ack    |
|--------------|-----------|--------|---------|--------|-------|---------|-------|----------|---------------|--------|
| /            | my_queue  | classic | Args    | running | 0     | 0       | 0     | 0.40/s   | 0.40/s        | 0.40/s |
