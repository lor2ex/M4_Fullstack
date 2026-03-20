## Обработка ошибок при работе FastAPI с внешними API

### 1. Почему это важно

Когда FastAPI взаимодействует с внешними API (например, сторонние сервисы, базы данных через HTTP, платёжные системы):

* сеть может быть недоступна;
* API может вернуть **ошибку клиента** (4xx) или **ошибку сервера** (5xx);
* ответы могут быть некорректными или неполными;
* таймауты могут привести к зависанию маршрута.

Если ошибки не обработать, API выдаёт **500 Internal Server Error**, и клиент не поймёт, что произошло.

---

### 2. Используем `httpx` для async запросов

`httpx` — современная асинхронная HTTP-библиотека, полностью совместимая с FastAPI.

```python
import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()
```

---

### 3. Обработка ошибок запроса

```python
@app.get("/get-user/{user_id}")
async def get_user(user_id: int):
    url = f"https://jsonplaceholder.typicode.com/users/{user_id}"

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()  # выбросит httpx.HTTPStatusError для 4xx/5xx

        except httpx.RequestError as exc:
            # Ошибка сети, таймаута и др.
            raise HTTPException(
                status_code=503,
                detail=f"External API request failed: {exc}"
            )

        except httpx.HTTPStatusError as exc:
            # Внешний API вернул 4xx или 5xx
            raise HTTPException(
                status_code=502,  # Bad Gateway
                detail=f"External API returned {exc.response.status_code}"
            )

    return response.json()
```

**Пояснение:**

* `RequestError` — проблемы с сетью или таймаут.
* `HTTPStatusError` — статус ответа 4xx или 5xx.
* Мы возвращаем **дружелюбные HTTP-коды для клиента**:

  * 502 Bad Gateway — внешняя ошибка сервиса;
  * 503 Service Unavailable — сеть недоступна.

---

### 4. Используем таймауты и повторные попытки

Важно **не зависать на медленном внешнем сервисе**:

```python
import asyncio

@app.get("/get-posts")
async def get_posts():
    url = "https://jsonplaceholder.typicode.com/posts"

    timeout = httpx.Timeout(3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        retries = 3
        for attempt in range(retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.RequestError:
                if attempt < retries - 1:
                    await asyncio.sleep(1)  # пауза перед повтором
                else:
                    raise HTTPException(status_code=503, detail="External API unavailable")
```

* Это гарантирует, что ваш API **не будет бесконечно ждать**, а клиент получит понятный ответ при сбое.

---

### 5. Логирование ошибок внешнего API

Обязательно логируйте ошибки для мониторинга:

```python
import logging

logger = logging.getLogger("external_api")

@app.get("/posts-logged")
async def posts_logged():
    url = "https://jsonplaceholder.typicode.com/posts"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error(f"External API error: {exc}")
            raise HTTPException(status_code=502, detail="External service error")
```

* В логах вы увидите, какие ошибки происходят при обращении к внешнему сервису.

---

### 6. Работа с несколькими внешними API

Если делаете несколько запросов параллельно, используйте `asyncio.gather` с `return_exceptions=True`:

```python
import asyncio

async def fetch_url(client, url):
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return e  # обработаем позже

@app.get("/multiple-apis")
async def multiple_apis():
    urls = [
        "https://jsonplaceholder.typicode.com/posts",
        "https://jsonplaceholder.typicode.com/users"
    ]

    async with httpx.AsyncClient(timeout=5.0) as client:
        results = await asyncio.gather(*(fetch_url(client, u) for u in urls), return_exceptions=True)

    # Разделяем успешные ответы и ошибки
    data = []
    errors = []
    for r in results:
        if isinstance(r, Exception):
            errors.append(str(r))
        else:
            data.append(r)

    if errors:
        # Можно вернуть частичный результат
        return {"data": data, "errors": errors}

    return {"data": data}
```

* Даже если один сервис упал, остальные результаты не теряются.
* Легко логировать ошибки и возвращать частичный результат клиенту.

---

### 7. Итоги

При работе с внешними API в FastAPI:

1. **Используйте async клиент** (`httpx.AsyncClient`) для неблокирующих запросов.
2. **Обрабатывайте исключения**:

   * `httpx.RequestError` для сетевых проблем;
   * `httpx.HTTPStatusError` для 4xx/5xx.
3. **Добавляйте таймауты и retries** для устойчивости.
4. **Логируйте ошибки** для мониторинга.
5. **Используйте `asyncio.gather(..., return_exceptions=True)`**, если делаете несколько параллельных запросов.
6. **Возвращайте клиенту дружелюбные HTTP-коды** (502, 503), не раскрывая детали внутреннего API.

