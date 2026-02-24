### Простые эндпойнты для CRUD Redis в FastAPI

#### 1. Установка пакетов:

```bash
pip install fastapi uvicorn[standard] redis
```

#### 2. Схема проекта

```
redis_project/
├── .venv/
├── docker-compose.yml
└── main.py
```

Файл `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
```


#### 2. Базовое подключение Redis через lifespan (рекомендуемый способ)
Используем `lifespan` для инициализации и закрытия соединения. Это чистый и современный подход.

```python
import asyncio
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response, Request, HTTPException
from redis.asyncio import Redis

CACHE_LIFETIME = 30

# Настраиваем Redis
redis = Redis(host='localhost', port=6379, decode_responses=True)

# Жизненный цикл приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ----------------------
    #        STARTUP
    # ----------------------

    # Провека соединения с Redis в начале работы
    await redis.ping()
    print("Redis подключён ✅")
    yield

    # ----------------------
    #       SHUTDOWN
    # ----------------------

    # Закрытие соединения при завершении работы
    await redis.close()
    print("Redis отключён ❌")

app = FastAPI(lifespan=lifespan)

# Зависимость для доступа к Redis
async def get_redis() -> Redis:
    return redis
```

Запуск: `uvicorn main:app --reload`

#### 4. Простое кэширование ответа эндпойнта

Создаём три эндпойнта для 
* добавления пары ключ - значения
* получения значения по ключу
* удаления пары по ключу

```python
# Зависимость для доступа к Redis
async def get_redis() -> Redis:
    return redis

# Сохранение значения в Redis
@app.get("/set/{key}/{value}")
async def set_value(key: str, value: str, client: Redis = Depends(get_redis)):
    await client.set(key, value, ex=CACHE_LIFETIME)
    ttl_seconds = await client.ttl(key)
    return {"status": "OK", "key": key, "value": value, "remaining time": ttl_seconds}


# Получение значения из Redis
@app.get("/get/{key}")
async def get_value(key: str, client: Redis = Depends(get_redis)):
    value = await client.get(key)
    ttl_seconds = await client.ttl(key)
    return {"key": key, "value": value or "Not found", "remaining time": ttl_seconds}


# Удаление ключа из Redis
@app.get("/delete/{key}")
async def delete_value(key: str, client: Redis = Depends(get_redis)):
    deleted = await client.delete(key)
    # status 0 - ключ не найден
    # status 1 - ключ был и удалён
    return {"key": key, "status": deleted}
```

Функция `get_redis()` создана для того, чтобы правильно и удобно подключать Redis через механизм зависимостей FastAPI.

Благодаря этому в каждый эндпойнты мы можем передавать объект `client` с помощью механизма зависимостей:  
`client: Redis = Depends(get_redis)`.

Теперь, через `client` мы можем взаимодействовать с async Redis.


##### 4.1. `GET /set/{key}/{value}` — сохранение значения в Redis

Сохраняет пару **ключ–значение** в Redis с ограниченным временем жизни (`CACHE_LIFETIME` секунд).

⚠️ Использование `GET` для изменения состояния сервера сделано **в учебных целях** и не рекомендуется для продакшена.

Запрос [http://127.0.0.1:8000/set/hello/world](http://127.0.0.1:8000/set/hello/world)  

вернёт

```json
{
  "status": "OK",
  "key": "hello",
  "value": "world",
  "remaining time": 30
}
```

---

##### 4.2. `GET /get/{key}` — получение значения из Redis

Возвращает значение по ключу из Redis и оставшееся время его жизни.


Запрос [http://127.0.0.1:8000/get/hello](http://127.0.0.1:8000/get/hello)  

вернёт

```json
{
  "key": "hello",
  "value": "Not found",
  "remaining time": 25
}
```

Либо, если ключ отсутствует, вернётся

```json
{
  "key":"hello",
  "value":"Not found",
  "remaining time":-2
}
```

---

##### 4.3. GET /delete/{key}` — удаление ключа из Redis

Удаляет ключ и его значение из Redis.

⚠️ Использование `GET` для удаления сделано **только для демонстрации**.

При запросе [http://127.0.0.1:8000/delete/hello](http://127.0.0.1:8000/delete/hello)

1. Выполняется команда Redis `DEL`.
2. Redis возвращает:

   * `1` — ключ существовал и был удалён
   * `0` — ключ не найден


```json
{
  "key": "hello",
  "status": 1
}
```

