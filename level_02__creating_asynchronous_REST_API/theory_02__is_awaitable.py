"""
В этом коде участвуют 2 типа задержки sleep:
эвейтэбл и нет.

Проверяется с помощью метода isawaitable() пакета inspect.

Если да:
- запускаем concurrency (квази-параллельно)
Если нет:
- запускаем как обычные функции

Иными словами, эта строчка кода:

    tasks = [sleep_object(1) for _ in range(3)]

в разных случаях выполняет различные действия


1. Если объекты НЕ эвейтэбл:

Просто поочерёдно вызывает функции sleep_object(1)

2. Если объекты эвейтэбл:

Создаёт список из трёх awaitable объектов, которые сразу не выполняются.
Но будут выполнены, когда они станут задачами внутри asyncio.gather(*tasks)


⚠️ ВАЖНО:
        results = await asyncio.gather(*tasks)

Здесь results никуда не возвращается, но гарантирует
правильное выполнение кода внутри asyncio.gather(*tasks).

"""


import asyncio
import time
import inspect

# --- Блокирующий объект ---
def blocking_sleep(n):
    print(f"Start blocking_sleep({n})")
    time.sleep(n)  # блокирует поток
    print(f"End blocking_sleep({n})")
    return n

# --- Эвейтэбл объект ---
async def awaitable_sleep(n):
    print(f"Start async_sleep({n})")
    await asyncio.sleep(n)  # awaitable
    print(f"End async_sleep({n})")
    return n

# --- Тест функций ---
async def main(sleep_object):
    start = time.time()

    tasks = [sleep_object(1) for _ in range(3)]


    if all(inspect.isawaitable(t) for t in tasks):
        print("All tasks are awaitable")
        results = await asyncio.gather(*tasks)
    else:
        print("Not all tasks are awaitable")

    print("Total time:", time.time() - start)


# --- Вариант # 1 (обычные функции) ---
asyncio.run(main(blocking_sleep))

# --- Вариант # 2 (эвейтэбл функции, или корутины) ---
# asyncio.run(main(awaitable_sleep))

