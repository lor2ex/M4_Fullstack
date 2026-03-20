## Параметры настройки CORS в FastAPI

### Пример реализации CORS

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Cписок разрешённых ресурсов
    allow_credentials=True,     # Разрешить отправку cookie (да или нет)
    allow_methods=["*"],        # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"],        # Разрешить все заголовки
)
```

* `CORSMiddleware` делает одно главное:
  * добавляет нужные `Access-Control-*` заголовки в ответ
* И иногда:
  * обрабатывает preflight (OPTIONS) запросы

Preflight запрос нужен только тогда, когда основной запрос может 
* "повредить” серверу 
* или требует особых разрешений:

| Причина                       | Пример                           |
| ----------------------------- | -------------------------------- |
| Метод не simple               | PUT, DELETE, PATCH               |
| Заголовок нестандартный       | X-CSRF-Token, Authorization      |
| Content-Type нестандартный    | application/json                 |
| Используются куки/credentials | fetch с `credentials: "include"` |

---

### 1. Основные параметры

#### 1.1. Параметр `allow_origins`

```python
allow_origins=[
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
```

##### Что делает?

* Определяет, какие origin могут читать ответ
* Влияет на заголовок:

```http
Access-Control-Allow-Origin: http://127.0.0.1:5500
```

---

##### Важные нюансы

* `"*"` -> разрешает всем
* но ❗ нельзя использовать с `allow_credentials=True`

---

##### Частая ошибка

```python
allow_origins=["http://localhost:5500"]
```

А запрос с:

```
http://127.0.0.1:5500
```

не совпадёт (это разные origin)

---

#### 1.2. Параметр `allow_credentials`

```python
allow_credentials=True
```

##### Что делает?

* Разрешает браузеру:

  * отправлять cookies
  * отправлять Authorization headers

* добавляет:

```http
Access-Control-Allow-Credentials: true
```

---

##### Критически важно

* Если `allow_credentials=True`, 
  * то нельзя разрешать отправлять cookies для всех:

```python
allow_origins=["*"]
```

* Почему?
  * это небезопасно

---

#### 1.3. Параметр `allow_methods`

```python
allow_methods=["*"]
```

##### Что делает?

* Определяет, какие HTTP-методы разрешены
* используется в **preflight (OPTIONS)**:

```http
Access-Control-Allow-Methods: GET, POST, PUT
```

Например, если в `allow_methods=["*"]` (разрешены все методы), то FastAPI через CORS middleware автоматически  
отвечает браузеру стандартным набором методов, которые поддерживаются CORS.

##### Пример `preflight` (предварительного) запроса:

```http
OPTIONS /items
Origin: https://other.com
Access-Control-Request-Method: PATCH
```

Если `allow_methods=["*"]` в CORS, сервер вернёт примерно:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: *
```


---

#### 1.4. Параметр `allow_headers`

```python
allow_headers=["*"]
```

##### Что делает?

Разрешает кастомные заголовки:

```http
Access-Control-Allow-Headers: X-CSRF-Token, Authorization
```

Например, если для разрешённой авторизации нужны заголовки:

```
headers: {
  "X-CSRF-Token": "...",
  "Authorization": "Bearer ..."
}
```

то без разрешения этих заголовков будет ошибка.

---

### 2. Дополнительные ("редкие") параметры

#### 2.1. `expose_headers`

Если фронтенду нужно читать нестандартные заголовки ответа, например `X-Total-Count`, `X-RateLimit-Remaining`,  

стандартного `allow_headers= [*]` будет уже недостаточно.

Необходимо будет добавить

```python
expose_headers=["X-Total-Count"]
```

* Без этого JS не сможет их прочитать: `response.headers.get("X-Total-Count")` вернёт `null`.
* Не влияет на отправку запроса, только на чтение ответа.

---

#### 2.2. `max_age`

Можно указать, на сколько секунд браузер будет кэшировать preflight запрос (OPTIONS):

```python
max_age=3600  # 1 час
```

* Уменьшает количество preflight-запросов при частых вызовах API.
* Не критично, но повышает производительность для активных приложений.

---

#### 3. `allow_origin_regex` (редко)

Если необходимо разрешить динамические поддомены через регулярные выражения, например:

```python
allow_origin_regex=r"https://.*\.example\.com"
```

* Полезно, если много поддоменов, а не удобно их перечислять в списке `allow_origins`.
* Обычно в локальной разработке и небольших проектах не нужен.

---

### Итого

Для большинства проектов достаточно:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

* Добавляем `expose_headers`, только если JS должен читать нестандартные заголовки ответа.
* Добавляем `max_age`, если необходимо уменьшить количество `preflight` запросов.
* `allow_origin_regex` и другие редко используемые параметры — только при специфических задачах.
