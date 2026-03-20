### Цель эксперимента

Показать разницу между:

1. **`requests` + ThreadPoolExecutor**
   → обычный код, вынесенный в потоки
2. **`httpx.AsyncClient` + event loop**
   → asyncio-совместимы код в нативной `loop event` FastAPI

С:

* одинаковой логикой
* одинаковой нагрузкой
* замером времени

---

### Структура проекта

```
fastapi_http_compare/
├── main.py
├── requirements.txt
└── load_test.py
```

---

### 1. Установка зависимостей

```bash
pip install fastapi[standard] uvicorn httpx requests

pip freeze > requirements.txt
```

---

### 2. FastAPI-приложение

`main.py`

```python
from fastapi import FastAPI
import time
import requests
import httpx
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

TIMES = 20
# -----------------------------
# Общая функция-мишень
# -----------------------------
EXTERNAL_URL = "https://httpbin.org/delay/1"

# -----------------------------
# 1. requests + ThreadPoolExecutor
# -----------------------------

executor = ThreadPoolExecutor(max_workers=TIMES)

def blocking_request():
    r = requests.get(EXTERNAL_URL)
    return r.status_code

@app.get("/requests-thread")
async def requests_thread():
    loop = asyncio.get_running_loop()
    start = time.perf_counter()

    # 5 параллельных HTTP-запросов
    tasks = [
        loop.run_in_executor(executor, blocking_request)
        for _ in range(TIMES)
    ]
    await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    return {
        "method": "requests + threads",
        "elapsed_seconds": round(elapsed, 2)
    }

# -----------------------------
# 2. httpx + event loop
# -----------------------------

@app.get("/httpx-async")
async def httpx_async():
    start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(EXTERNAL_URL)
            for _ in range(TIMES)
        ]
        await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    return {
        "method": "httpx + event loop",
        "elapsed_seconds": round(elapsed, 2)
    }
```

#### Важное пояснение

`asyncio.get_running_loop()` **сама по себе не делает `requests` async-совместимой**.   
Библиотека `requests` остаётся полностью блокирующей `event_loop`.    
НО! 
Благодаря `ThreadPoolExecutor` — мы **переносим блокирующий вызов в отдельный поток**,   
чтобы основной `async`-цикл (`asyncio` loop) не блокировался.  

То есть:

* `requests.get` **блокирует поток**, в котором выполняется.
* Когда мы запускаем его через `loop.run_in_executor(executor, blocking_request)`,   
  он выполняется **в отдельном потоке пула `ThreadPoolExecutor`**.
* Основной `async` код FastAPI остаётся свободным и может обрабатывать другие запросы.

По сути:

```python
result = await loop.run_in_executor(executor, blocking_request)
```

* `loop.run_in_executor` — это мост между синхронным и асинхронным кодом.
* `await` ждёт завершения задачи **асинхронно**, не блокируя event loop.

---

#### Краткий аналог:

* **Без `run_in_executor`**: `requests.get` блокирует весь сервер FastAPI на время запроса.
* **С `run_in_executor`**: `requests.get` выполняется в другом потоке, а FastAPI продолжает обслуживать другие запросы.

---

### 3. Запуск сервера

```bash
uvicorn main:app --reload
```

---

### 4. Ручная проверка

Откройте в браузере или через curl:

```bash
curl http://localhost:8000/requests-thread
curl http://localhost:8000/httpx-async
```

Оба эндпоинта:

* выполняют **5 HTTP-запросов**
* каждый запрос ждёт **1 секунду**

---

### 5. Нагрузочный тест

#### 5.1. Асинхронность выполнена с помощью `asyncio`

`load_test.py`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import requests

URLS = [
    "http://localhost:8000/requests-thread",
    "http://localhost:8000/httpx-async",
]

REPEAT = 10

# Создаем пул потоков
executor = ThreadPoolExecutor(max_workers=10)


def blocking_request(url):
    """Синхронный запрос, который будем запускать в отдельном потоке"""
    r = requests.get(url)
    return r.status_code


async def run(url, n=10):
    """Асинхронная функция, которая запускает n запросов параллельно"""
    loop = asyncio.get_running_loop()
    start = time.perf_counter()

    # Запускаем каждый запрос в отдельном потоке
    tasks = [loop.run_in_executor(executor, blocking_request, url) for _ in range(n)]

    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    print(f"{url} -> {round(elapsed, 2)} sec")


async def main():
    # Запускаем все URL параллельно
    await asyncio.gather(*(run(url, REPEAT) for url in URLS))


if __name__ == "__main__":
    asyncio.run(main())

```

#### 5.2. Асинхронность выполнена с помощью `threads`

`load_test.py`

```python
import time
from concurrent.futures import ThreadPoolExecutor
import requests

URLS = [
    "http://localhost:8000/requests-thread",
    "http://localhost:8000/httpx-async",
]

REPEAT = 1

def blocking_request(url):
    """Синхронный блокирующий запрос"""
    r = requests.get(url)
    return r.status_code


def run(url, n=10, max_workers=10):
    """Выполняем n запросов параллельно через ThreadPoolExecutor"""
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # submit возвращает Future, который можно использовать для получения результата
        futures = [executor.submit(blocking_request, url) for _ in range(n)]

        # ждем завершения всех задач и собираем результаты
        results = [f.result() for f in futures]

    elapsed = time.perf_counter() - start
    print(f"{url} -> {round(elapsed, 2)} sec | Results: {results}")


if __name__ == "__main__":
    for url in URLS:
        run(url, n=REPEAT, max_workers=10)
```

Запуск:

```bash
python load_test.py
```

---

### 6. Что вы должны увидеть (типично)

| Подход             | 1 запроса  | 5 запросов | 10 запросов |
| ------------------ |------------|------------|-------------|
| requests + threads | 3.25       | 11.02      | 20.51       |
| httpx + event loop | 2.84       | 3.38       | 5.52        | 

При **малой нагрузке** разница минимальна.

---

### 7. Где разница становится очевидной

Увеличьте:

* количество внешних запросов (`10`, `20`)
* количество одновременных клиентов
* уменьшите `max_workers`

Тогда:

### requests + threads

* растёт потребление памяти
* растёт overhead потоков
* начинается деградация

### httpx + event loop

* I/O масштабируется
* нет лишних потоков
* event loop остаётся отзывчивым

**Важно**:
`httpx` не быстрее *по времени одного запроса* —
он **масштабируется лучше**.

---

### 8. Ключевой вывод

> **`requests` + `threads` решает проблему блокировки,
> `httpx` + event loop устраняет её архитектурно и более продуктивно.**
