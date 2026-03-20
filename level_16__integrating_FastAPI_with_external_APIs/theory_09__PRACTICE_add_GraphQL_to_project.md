Добавим **GraphQL как третий способ вызвать ту же нагрузку**, но уже через схему и резолверы.

Наша цель — не заменить REST, а показать:

* те же `TIMES` запросов
* та же логика
* но вызов через GraphQL

---

### 1. Схема GraphQL

Мы добавим:

* тип `BenchmarkResult`
* два query-поля:

  * `requestsThread`
  * `httpxAsync`

---

### Концептуальная схема

```graphql
type BenchmarkResult {
  method: String!
  elapsedSeconds: Float!
}

type Query {
  requestsThread: BenchmarkResult!
  httpxAsync: BenchmarkResult!
}
```

---

## 2. Установка Strawberry

```bash
pip install strawberry-graphql

pip freeze > requirements.txt
```

(для FastAPI дополнительных пакетов не нужно)

---

### 3. Добавляем в `main.py`

Добавляем GraphQL в ваш существующий файл.

```python
import strawberry
from strawberry.fastapi import GraphQLRouter


# ---------------------------------------------------
# GraphQL часть
# ---------------------------------------------------

@strawberry.type
class BenchmarkResult:
    method: str
    elapsed_seconds: float


@strawberry.type
class Query:

    @strawberry.field
    async def requests_thread(self) -> BenchmarkResult:
        loop = asyncio.get_running_loop()
        start = time.perf_counter()

        tasks = [
            loop.run_in_executor(executor, blocking_request)
            for _ in range(TIMES)
        ]
        await asyncio.gather(*tasks)

        return BenchmarkResult(
            method="requests + threads",
            elapsed_seconds=round(time.perf_counter() - start, 2)
        )

    @strawberry.field
    async def httpx_async(self) -> BenchmarkResult:
        start = time.perf_counter()

        async with httpx.AsyncClient() as client:
            tasks = [
                client.get(EXTERNAL_URL)
                for _ in range(TIMES)
            ]
            await asyncio.gather(*tasks)

        return BenchmarkResult(
            method="httpx + event loop",
            elapsed_seconds=round(time.perf_counter() - start, 2)
        )


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")
```

---

## 4. Запуск

Теперь нам доступны:

* REST:

  * `/requests-thread`
  * `/httpx-async`

* GraphQL:

  * `/graphql`
  * `/graphql` (GraphiQL UI в браузере)

---

### 5. Пример GraphQL-запроса

#### Откройте:

[http://localhost:8000/graphql](http://localhost:8000/graphql)

#### И выполните:

```graphql
query {
  requestsThread {
    method
    elapsedSeconds
  }
}
```

---

#### Мы увидим

```json
{
  "data": {
    "requestsThread": {
      "method": "requests + threads",
      "elapsedSeconds": 3.23
    }
  }
}
```

---

#### Можно выполнить оба сразу:

```graphql
query {
  requestsThread {
    elapsedSeconds
  }
  httpxAsync {
    elapsedSeconds
  }
}
```

---

#### И получим

```json
{
  "data": {
    "requestsThread": {
      "elapsedSeconds": 3.02
    },
    "httpxAsync": {
      "elapsedSeconds": 2.83
    }
  }
}
```

---

### Что важно понять

1. GraphQL не меняет модель исполнения.
2. Он просто вызывает те же резолверы.
3. Внутри резолвера мы всё равно:

   * либо используем ThreadPoolExecutor
   * либо event loop
4. GraphQL — это слой запроса, а не модель параллелизма.

---