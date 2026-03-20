### 1. Библиотека `httpx`

**`httpx`** — это HTTP-клиентская библиотека для Python, которая предоставляет:

* **синхронный API**
* **awaitable API**, предназначенный для работы в event loop (например, `asyncio`)
* единый интерфейс для обоих режимов

**Ключевая идея**:

> *`httpx` — это HTTP-клиент, способный работать в неблокирующем I/O-контексте, если его корректно использовать.*

---

### 2. Принципиально важное уточнение

❗ **Поддержка `asyncio` ≠ асинхронность исполнения кода**

`httpx.AsyncClient`:

* **не делает код параллельным**
* **не создаёт фоновые потоки**
* **не гарантирует выигрыша по времени**

Он лишь:

* **не блокирует event loop во время I/O**
* позволяет **квази-параллельное выполнение I/O-операций**
  (cooperative multitasking)

---

### 3. Минимальные примеры `httpx`

#### Обычный режим (блокирующий `event loop`)

```python
import httpx

response = httpx.get("https://api.example.com/users/1")
print(response.json())
```

**Полностью аналогично `requests` по модели исполнения.**

---

#### `async` режим (не блокирующий `event loop`)

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.example.com/users/1")
        print(r.json())

asyncio.run(main())
```

**Здесь**:

* код **кооперативно уступает управление** (`concurrency` == квази-параллелизм)
* `event loop` может выполнять **другие задачи**

---

### 4. Библиотека `requests`

**`requests`** — синхронный HTTP-клиент:

* блокирует поток выполнения
* прост в использовании
* идеально подходит для:

  * CLI
  * batch-скриптов
  * линейных сценариев

```python
import requests

r = requests.get("https://api.example.com/users/1")
print(r.json())
```

**Никакого взаимодействия с `event loop` не предусмотрено.**

---

### 5. Принципиальная разница `requests` vs `httpx`

| Критерий                                   | requests | httpx                       |
|--------------------------------------------|--| --------------------------- |
| Работа с `event loop`                      | ❌ | ✅                           |
| Совместимость с `asyncio`                  | ❌ | ✅                           |
| Асинхронность через `asyncio`              | ❌ | ✅                           |
| Асинхронность через `threads` / `multiprocess` | ✅ | ✅                           |
| Реальный параллелизм                       | ❌ | ❌                           |
| HTTP/2                                     | ❌ | ✅                           |


**Ни одна из этих библиотек не создаёт параллелизм сама по себе.**

---

### 6. Использование с FastAPI 

## ❌ Почему `requests` — плохой выбор

```python
@app.get("/proxy")
async def proxy():
    r = requests.get("https://api.example.com/data")
    return r.json()
```

* блокируется `event loop`
* остальные корутины **не могут выполняться**
* падает пропускная способность сервера

---

## ✅ Почему `httpx.AsyncClient` — правильный выбор

```python
@app.get("/proxy")
async def proxy():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.example.com/data")
        return r.json()
```

* I/O **не блокирует `event loop`**
* возможен **квази-параллелизм запросов** без использования внешних библиотек
* FastAPI сохраняет способность обслуживать другие соединения


