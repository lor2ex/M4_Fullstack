### На "зачёт": что такое GraphQL?

**GraphQL** — это язык запросов к API и спецификация выполнения этих запросов.
Он описывает:

1. **Схему данных** (типизированный контракт API)
2. **Форму запроса**
3. **Форму ответа (строго соответствует запросу)**

В отличие от REST, клиент сам определяет, какие поля ему нужны.

---

### Минимальный пример (концепция)

#### Схема

```graphql
type User {
  id: ID!
  name: String!
  email: String!
}

type Query {
  user(id: ID!): User
}
```

### Запрос клиента

```graphql
query {
  user(id: 1) {
    id
    name
  }
}
```

### Ответ

```json
{
  "data": {
    "user": {
      "id": "1",
      "name": "Alice"
    }
  }
}
```

**В ответе нет `email`, потому что клиент его не запросил.**

---

#### Что это даёт?

GraphQL решает три ключевые задачи:

1. **Нет overfetching** (лишних данных)
2. **Нет underfetching** (несколько REST-запросов вместо одного)
3. **Жёсткая схема и типизация**

---

### Архитектурная модель

REST:

```
GET /users/1
GET /users/1/posts
GET /users/1/friends
```

GraphQL:

```
POST /graphql
```

С телом запроса, описывающим всё нужное дерево данных.

---

### GraphQL и FastAPI

FastAPI — это ASGI-фреймворк.
GraphQL в FastAPI подключается через стороннюю библиотеку.

Чаще всего используют:

* `strawberry`
* `graphene`
* `ariadne`

На практике для FastAPI чаще берут **Strawberry**, потому что он:

* нативно поддерживает async
* использует Python type hints
* хорошо интегрируется с FastAPI

---

#### Пример GraphQL в FastAPI (Strawberry)

```python
from fastapi import FastAPI
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class User:
    id: int
    name: str

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> User:
        return User(id=id, name="Alice")

schema = strawberry.Schema(query=Query)

app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

Запуск:

```
uvicorn main:app
```

Теперь:

```
POST /graphql
```

Тело:

```graphql
query {
  user(id: 1) {
    id
    name
  }
}
```

---

### Как это работает внутри FastAPI?

1. FastAPI принимает HTTP POST
2. GraphQLRouter передаёт запрос в GraphQL-движок
3. Движок:

   * валидирует запрос по схеме
   * строит execution plan
   * вызывает резолверы
   * формирует строго структурированный ответ

Важно:

* REST в FastAPI — это обычные path-операции
* GraphQL — это **один endpoint**, внутри которого работает свой механизм маршрутизации

---

### Где GraphQL полезен?

1. Сложные связанные данные
2. Мобильные клиенты
3. SPA
4. Когда важна строгая схема API

---

### Где REST проще?

1. Простые CRUD-сервисы
2. Публичные API
3. Когда нужна прозрачность HTTP-механики (коды, кеширование, CDN)

---

### Главное отличие концептуально

REST — это **ресурсная модель**.
GraphQL — это **запрос к графу данных**.

REST:

> «Дай мне ресурс /users/1»

GraphQL:

> «Дай мне user 1, но только id и name»


