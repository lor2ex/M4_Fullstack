### 1. Backend без CORS (получим ошибку)

Добавляем зависимости:

```bash
pip install fastapi[standard]

pip freeze > requirements.txt
```

Создадим файл `main.py`

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API Home page"}

@app.get("/hello")
def hello():
    return {"message": "Hello from API"}
```

Запускаем сервер:

```bash
uvicorn main:app --reload
```

API будет доступен:

```
http://localhost:8000/
```

---

### 2. Простой frontend

Создадим файл `index.html`.

```html
<!DOCTYPE html>
<html>
<body>

<h1>CORS demo</h1>

<button onclick="loadData()">Load data</button>

<script>
async function loadData() {
    const res = await fetch("http://localhost:8000/hello")
    const data = await res.json()
    console.log(data)
}
</script>

</body>
</html>
```

Запускаем этот файл по адресу: [http://localhost:5500/index.html](http://localhost:5500/index.html)

```bash
python -m http.server 5500
```

И пробуем нажать кнопку `Load data`

---

### 3. Ошибка CORS

В **Console** браузера появится ошибка:

```
Cross-Origin Request Blocked: 
The Same Origin Policy disallows reading the remote resource at http://localhost:8000/hello. 
(Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
```

Почему?

* страница открыта из **[http://127.0.0.1:5500/**
* API на **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

Это **разные origin**, поэтому браузер блокирует ответ.

Об это явно указано на вкладке `Network` инспектора браузера:

`Response Headers`

```
HTTP/1.1 200 OK
date: Wed, 18 Mar 2026 17:47:39 GMT
server: uvicorn
content-length: 28
content-type: application/json
```

---

### 4. Исправляем CORS в FastAPI

1. Добавляем адрес фронтэнда в `origins`
2. Добавляем middleware.

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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

@app.get("/hello")
def hello():
    return {"message": "Hello from API"}
```

---

### 5. Теперь всё работает

Если frontend запущен, например, через **Live Server**:

```
http://localhost:5500
```

то запрос:

```javascript
fetch("http://localhost:8000/hello")
```

вернёт в консоль браузера:

```json
{
  "message": "Hello from API"
}
```

И ошибки CORS больше не будет.

#### Изменился и ответ браузера:

**Было (без CORS)**
`Response Headers`
```
HTTP/1.1 200 OK
date: Wed, 18 Mar 2026 17:47:39 GMT
server: uvicorn
content-length: 28
content-type: application/json
```
* Сервер просто отвечает, 
  * но **браузер блокирует доступ к ответу**, если запрос пришёл с другого origin 
  * (в нашем случае `127.0.0.1:5500 → 127.0.0.1:8000`).

* ⚠️ Важно:
  * Запрос **доходит до сервера и выполняется**
  * ❗ Но браузер говорит: *“нельзя читать ответ”*


**Стало (с CORS)**
  `Response Headers`
```
HTTP/1.1 200 OK
date: Wed, 18 Mar 2026 17:45:02 GMT
server: uvicorn
content-length: 28
content-type: application/json
access-control-allow-credentials: true
access-control-allow-origin: http://127.0.0.1:5500
vary: Origin
```

Добавились два ключевых заголовка:

1. `access-control-allow-origin` (Самый главный заголовок!)

Этот заголовок как бы говорит браузеру:
> “Я разрешаю этому origin (`127.0.0.1:5500`) читать мой ответ”
Если бы его не было — браузер бы блокировал ответ

---

2. `access-control-allow-credentials`

Разрешает передавать:

* cookies
* authorization headers
* session данные

**Итог разницы**

| Было                   | Стало                        |
| ---------------------- | ---------------------------- |
| Сервер просто отвечает | Сервер явно разрешает доступ |
| Браузер блокирует      | Браузер пропускает           |
| Нет CORS               | Есть CORS                    |
| Нет `Access-Control-*` | Есть нужные заголовки        |


---

### 6. Самый простой вариант для разработки

Иногда делают так:

```python
allow_origins=["*"]
```

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

⚠️ Но **в production это небезопасно**.

---

### Итог

| Шаг                      | Что происходит          |
| ------------------------ | ----------------------- |
| Без CORS                 | браузер блокирует ответ |
| Добавляем CORSMiddleware | сервер разрешает origin |
| Браузер читает ответ     | всё работает            |


