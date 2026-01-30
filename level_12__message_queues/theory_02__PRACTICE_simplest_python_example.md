## Ключевая идея, которую иллюстрируют примеры

> **Асинхронность — это не `async / await` и не тип очереди.
> Асинхронность — это перекрытие независимых операций по времени.**

MQ (message queue) становится асинхронной **только тогда**, когда:

* producer **не ждёт**, пока consumer закончит обработку;
* consumer может работать **параллельно** с производством сообщений
  (в потоках, процессах или через event loop).

---

### 1. Обычный Python — строго последовательное выполнение

```python
import time

print("1. Обычный Python — последовательный вызов\n")

queue = []  # простейшая, низко-производительная и потоко-ОПАСНАЯ очередь

# Producer
for i in range(1, 6):
    msg = f"Задача {i}"
    queue.append(msg)
    print(f"[P] → {msg}")
    time.sleep(0.3)

print()

# Consumer
while queue:
    msg = queue.pop(0)
    print(f"[C] ← {msg:<10} начало")
    time.sleep(1.0)
    print(f"[C]     {msg:<10} готово")
```

#### Что здесь происходит?

* Producer **полностью завершается**, прежде чем consumer начинает работу.
* Consumer блокирует выполнение на `sleep(1.0)`.
* Никакого перекрытия операций по времени нет.

**Итог:**
* полностью **синхронное** поведение MQ

---

### 2. Обычный Python + `threading` — асинхронный код и асинхронная MQ

```python
import threading
import queue
import time

print("2. Обычный Python + threading\n")

q = queue.Queue()

def producer():
    for i in range(1, 6):
        msg = f"Задача {i}"
        q.put(msg)
        print(f"[P] → {msg}")
        time.sleep(0.3)

def consumer():
    while True:
        try:
            msg = q.get(timeout=4.0)
            print(f"[C] ← {msg:<10} начало")
            time.sleep(1.0)
            print(f"[C]     {msg:<10} готово")
            q.task_done()
        except queue.Empty:
            break

print("Запуск потоков...\n")

p = threading.Thread(target=producer)
c = threading.Thread(target=consumer)

p.start()
c.start()

p.join()
c.join()
```

#### Что здесь происходит?

* Producer и consumer выполняются **в разных потоках**.
* Пока consumer «спит» 1 секунду, producer продолжает класть сообщения.
* Очередь выступает как **буфер и точка развязки по времени**.

**Итог:**
* асинхронное поведение без использования пакета `asincio`

---

### 3. Пакет `asyncio`, но полностью синхронная MQ

```python
import asyncio

async def main():
    print("3. asyncio — последовательный стиль\n")
    
    q = asyncio.Queue()

    # Producer — кладёт всё сразу
    for i in range(1, 6):
        msg = f"Задача {i}"
        await q.put(msg)
        print(f"[P] → {msg}")
        # нет await asyncio.sleep → нет уступки event loop

    print()

    # Consumer — строго после producer
    while not q.empty():
        msg = await q.get()
        print(f"[C] ← {msg:<10} начало")
        await asyncio.sleep(1.0)
        print(f"[C]     {msg:<10} готово")
        q.task_done()

    await q.join()

print("Запуск event loop...\n")
asyncio.run(main())
```

#### Что здесь происходит?

* Есть `async`, `await`, `asyncio.Queue`.
* **Но producer и consumer вызываются последовательно**.
* Event loop **не получает возможности** переключаться между ними.

**Итог:**
* поведение остаётся **синхронным**
* `asyncio.Queue` ≠ асинхронная MQ


---

### 4. `asyncio` — асинхронный код и асинхронная MQ

```python
import asyncio

async def producer(q):
    for i in range(1, 6):
        msg = f"Задача {i}"
        await q.put(msg)
        print(f"[P] → {msg}")
        await asyncio.sleep(0.3)

async def consumer(q):
    while True:
        try:
            msg = await asyncio.wait_for(q.get(), timeout=4.0)
            print(f"[C] ← {msg:<10} начало")
            await asyncio.sleep(1.0)
            print(f"[C]     {msg:<10} готово")
            q.task_done()
        except asyncio.TimeoutError:
            if q.empty():
                break

async def main():
    print("4. asyncio — конкурентный стиль\n")
    
    q = asyncio.Queue()
    
    p_task = asyncio.create_task(producer(q))
    c_task = asyncio.create_task(consumer(q))
    
    await asyncio.gather(p_task, c_task)

print("Запуск event loop...\n")
asyncio.run(main())
```

#### Что здесь происходит?

* Producer и consumer — **отдельные задачи**.
* `await asyncio.sleep()` отдаёт управление event loop.
* Пока consumer «ждёт», producer продолжает работу.

**Итог:**
* перекрытие операций по времени
* здесь `asyncio` действительно делает код асинхронным
* это настоящая асинхронная MQ

---

## Сравнение вариантов

| № | Вариант                   | Producer блокируется consumer-ом | Перекрытие по времени | Стиль кода  | Поведение по сути |
| - | ------------------------- | -------------------------------- | --------------------- | ----------- | ----------------- |
| 1 | Обычный Python            | Да                               | Нет                   | sync        | синхронное        |
| 2 | threading + Queue         | Нет                              | Да                    | sync        | асинхронное       |
| 3 | asyncio (последовательно) | Да                               | Нет                   | async/await | синхронное        |
| 4 | asyncio (tasks)           | Нет                              | Да                    | async/await | асинхронное       |

---

## Таким образом

> **Асинхронность — это не `asyncio` и не `Queue`.
> Асинхронность — это архитектурное свойство:
> producer и consumer не блокируют друг друга по времени.**

Поэтому:

* можно написать **синхронную MQ на asyncio**;
* можно написать **асинхронную MQ без asyncio**;
* и только квазипараллельное выполнение делает очередь *реально* асинхронной.


