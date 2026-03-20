## Диагностика и обработка ошибок CORS

### 1. Как выглядит ошибка CORS

В браузере ты почти всегда увидишь что-то вроде:

```
Access to fetch at 'http://127.0.0.1:8000' from origin 'http://127.0.0.1:5500'
has been blocked by CORS policy
```

⚠️ Важно:

> ❗ Это **ошибка браузера**, а не сервера

Сервер чаще всего **уже ответил нормально (200 OK)** — просто браузер не дал доступ к ответу.

---

### 2. Первый шаг диагностики (самый важный)

#### 2.1. Проверяем Request

* Открываем DevTools → Network
* Проверяем, был ли отправлен запрос вообще?

* ❌ Нет → проблема НЕ в CORS
* ✅ Есть → продолжаем

---

#### 2.1. Проверяем Response

В Response Headers проверяем заголовок `Access-Control-Allow-Origin`

| Вариант                        | Когда работает                              | Особенности                                                                              |
| ------------------------------ | ------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Конкретный origin              | Совпадает с Origin запроса                  | Можно использовать с credentials                                                         |
| `*`                            | Любой origin                                | **Нельзя** с credentials (cookies/Authorization)                                         |
| Нет заголовка                  | Заголовок отсутствует → запрос заблокирован | Браузер отклоняет кросс-доменный запрос                                                  |
| Несколько origin через запятую | ❌ Не работает                               | Если нужно несколько origin, сервер должен подставлять **конкретный Origin динамически** |



---

### 3. Типовые проблемы и как их решать

---

#### 3.1. Нет `Access-Control-Allow-Origin`

##### Симптом

В ответе:

```http
(no access-control-allow-origin)
```

##### Причина

CORS middleware не настроен

##### Решение

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
)
```

---

#### 3.2. Origin не совпадает

##### Симптом

```http
Access-Control-Allow-Origin: http://localhost:5500
```

А запрос с:

```
http://127.0.0.1:5500
```

Браузер блокирует

---

##### Решение

Добавить оба:

```python
allow_origins=[
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
```

---

#### 3.3. credentials + `*`

##### Симптом

```python
allow_origins=["*"]
allow_credentials=True
```

Браузер игнорирует заголовки

---

##### Решение

```python
allow_origins=["http://frontend.com"]
allow_credentials=True
```

---

#### 3.4. Preflight (OPTIONS) падает

##### Симптом

В Network есть:

```
OPTIONS → 405 Method Not Allowed
```

или

```
CORS error on OPTIONS
```

---

##### Причина

Сервер не разрешает:

* метод
* заголовки

---

##### Решение

```python
allow_methods=["*"]
allow_headers=["*"]
```

---

#### 3.5. Кастомные headers

##### Симптом

```
Request header field X-CSRF-Token is not allowed
```

---

##### Решение

```python
allow_headers=["*"]
```

или явно:

```python
allow_headers=["X-CSRF-Token", "Authorization"]
```

---

#### 3.6. Не видны response headers

##### Симптом

```javascript
response.headers.get("X-Total-Count") // null
```

---

##### Решение

```python
expose_headers=["X-Total-Count"]
```

---

### 4. Алгоритм диагностики (ещё раз "на зачёт")

##### 4.1. Есть ли запрос в Network?

* нет → не CORS

##### 4.2. Есть ли `Access-Control-Allow-Origin`?

* нет → middleware

##### 4.3. Совпадает ли origin?

* нет → добавить

##### 4.4. Есть ли OPTIONS?

* да → проверяем:

  * allow_methods
  * allow_headers

##### 4.5. Есть ли credentials?

* да → убираем `"*"` из разрешённых origin

