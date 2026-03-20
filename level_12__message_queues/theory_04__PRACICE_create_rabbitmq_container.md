### Создадим контейнер с RabbitMQ для первого знакомства.

`docker-compose.yml`:

```yaml
services:
  rabbitmq:
    image: rabbitmq:4-management  # ← сразу с плагином management UI
    container_name: rabbitmq-fun
    ports:
      - "5672:5672"       # AMQP протокол (для клиентов, т.е программ)
      - "15672:15672"     # веб-интерфейс управления (для людей)
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest

    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  rabbitmq-data:
```

```bash
docker compose up --build
```

Через 15–30 секунд после запуска преходим в **RabbitMQ Management UI** (веб-интерфейс управления RabbitMQ):

**http://localhost:15672**

Логин / пароль: **guest** / **guest**

### Что можно делать прямо в браузере (без кода — чисто исследование)

1. **Overview**
   * общая картина: 
     * сколько сообщений, 
     * соединений, 
     * очередей

2. **Queues** 
   * можно создать New Queue самостоятельно
   * или посмотреть очередь, которую далее мы создадим в коде

3. **Exchanges** 
    * правила обмена сообщениями

4. **Bindings**
   * связи между exchange и очередью

5. **Connections / Channels** 
   * как потребители подключаются

8. **Admin** 
    * управление подключением пользователей

