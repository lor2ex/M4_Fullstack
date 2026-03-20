### 0. Подготовка

Запустить базы данных

```bash
docker-compose up -d
```

Запустить приложение

```bash
uvicorn app.main:app --reload
```

Открыть Swagger

```
http://localhost:8000/docs
```

---

### 1. Пользователи (SQL)

#### Создание пользователя

**POST `/users/`**

```json
{
  "username": "alice",
  "email": "alice@example.com"
}
```
**Ответ:**

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

**Результат**:

* Пользователь создан
* Вернулся `id`

---

#### Получение пользователя

**GET `/users/{id}`**

Запрашиваем пользователя с `id=1`

**Ответ:**

```json
{
  "id": 1,
  "username": "alice",
  "email": "alice@example.com"
}
```

**Результат**:

* Пользователь найден
* Данные соответствуют отправленным

**Вывод:**

> Строгая структура, уникальные поля → SQL

---

### 2. Книги (SQL)

#### Создание книги

**POST `/products/`**

```json
{
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 39.99,
  "stock": 5
}
```

**Ответ**:

```json
{
  "id": 1,
  "title": "Clean Code",
  "author": "Robert C. Martin",
  "price": 39.99,
  "stock": 5
}
```

**Результат**:

* Книга создана
* `stock` сохранён

---

#### Получение всех книг

**GET `/products/`**

**Ответ**:

```json
[
  {
    "id": 1,
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "price": 39.99,
    "stock": 5
  }
]
```

**Результат**:

* Книга присутствует в списке

**Вывод:**

> Каталоги и справочники удобно хранить в SQL

---

### 3. Ключевой тест — заказ (SQL + транзакция)

#### Создание заказа

**POST `/orders/`**

```json
{
  "user_id": 1,
  "items": [
    { "product_id": 1, "quantity": 2 }
  ]
}
```

**Ответ**:

```json
{
  "id": 1,
  "user_id": 1,
  "status": "pending"
}
```

**Результат**:

* Заказ создан
* `stock` уменьшился с 5 до 3

---

#### Ошибка из-за нехватки товара

**POST `/orders/`**

```json
{
  "user_id": 1,
  "items": [
    { "product_id": 1, "quantity": 10 }
  ]
}
```
**Ответ**:

```json
{
  "detail": "Not enough stock for product 1"
}
```

**Результат**:

* Получена ошибка
* Заказ **не создан**
* `stock` **не изменился**

**Вывод (ОЧЕНЬ ВАЖНО):**

> Всё либо выполняется полностью, либо не выполняется вообще —
> **транзакции = главное преимущество SQL**

---

### 4. Платёж (SQL)

#### Оплата заказа

**POST `/payments/`**

```json
{
  "order_id": 1,
  "amount": 79.98
}
```

**Ответ**:

```json
{
  "id": 1,
  "order_id": 1,
  "amount": 79.98,
  "status": "completed"
}
```

**Результат**:

* Платёж создан
* Статус заказа изменён на `completed`

**Вывод:**

> Состояния и финансы должны быть в SQL

---

### 5. Отзывы (MongoDB)

#### Добавление отзыва

**POST `/reviews/`**

```json
{
  "product_id": 1,
  "username": "anon",
  "rating": 5,
  "comment": "Отличная книга!"
}
```

**Ответ**:

```json
{
  "id": "696867237398a30642da88d0",
  "product_id": 1,
  "user_id": null,
  "username": "anon",
  "rating": 5,
  "comment": "Отличная книга!",
  "created_at": "2026-01-15T04:03:47.008674+00:00"
}
```

**Результат**:

* Отзыв сохранён

---

#### Отзыв с другой структурой

**POST `/reviews/`**

```json
{
  "product_id": 1,
  "user_id": 1,
  "rating": 4,
  "comment": "Полезно",
  "likes": 10
}
```

**Ответ**:

```json
{
  "id": "696867537398a30642da88d1",
  "product_id": 1,
  "user_id": 1,
  "username": null,
  "rating": 4,
  "comment": "Полезно",
  "created_at": "2026-01-15T04:04:35.608305+00:00"
}
```

**Результат**:

* Отзыв сохранён
* Новое поле добавлено **без изменения схемы**

---

#### Получение отзывов

**GET `/reviews/product/1`**

**Ответ**:

```json
[
  {
    "id": "696867237398a30642da88d0",
    "product_id": 1,
    "user_id": null,
    "username": "anon",
    "rating": 5,
    "comment": "Отличная книга!",
    "created_at": "2026-01-15T04:03:47.008674+00:00"
  },
  {
    "id": "696867537398a30642da88d1",
    "product_id": 1,
    "user_id": 1,
    "username": null,
    "rating": 4,
    "comment": "Полезно",
    "created_at": "2026-01-15T04:04:35.608305+00:00"
  }
]
```

**Результат**:
* Возвращаются оба отзыва
* Структуры отличаются

**Вывод:**

> MongoDB удобна для пользовательского контента и быстро меняющихся данных

---

### 6. Негативные тесты

#### Заказ с несуществующим `product_id` → ошибка

**POST `/orders/`**

```json
{
  "user_id": 5,
  "items": [
    { "product_id": 1, "quantity": 10 }
  ]
}
```
**Ответ**:

```json
{
  "detail": "User 5 not found"
}
```


#### Платёж для несуществующего заказа → 404

**POST `/payments/`**

```json
{
  "order_id": 5,
  "amount": 79.98
}
```
**Ответ**:

```json
{
  "detail": "Order not found"
}
```

#### Отзыв без `rating` → 422

**POST `/reviews/`**

```json
{
  "product_id": 1,
  "user_id": 1,
  "comment": "Полезно",
  "likes": 10
}
```

**Ответ**:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "rating"
      ],
      "msg": "Field required",
      "input": {
        "product_id": 1,
        "user_id": 1,
        "comment": "Полезно",
        "likes": 10
      }
    }
  ]
}
```

**Вывод:**

> FastAPI + Pydantic ловят ошибки на уровне API
> SQL — на уровне данных

---

