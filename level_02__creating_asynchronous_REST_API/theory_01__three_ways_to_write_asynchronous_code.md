# Три способа создания асинхронного кода

[https://it4each.com/blog/threading-multiprocessing-i-asyncio-v-python/](https://it4each.com/blog/threading-multiprocessing-i-asyncio-v-python/)



## Сравнение `threading` и `asyncio`

[threading_vs_asyncio/main.py](threading_vs_asyncio/main.py)

## Вывод: 

Наиболее эффективный способ `concurrency` вычислений (квази-параллельных) — `asyncio`.

Но есть существенная оговорка: объект, используемый в этом коде, должен быть эвейтэбл (`awaitable`).

То есть иметь dunder метод `__await__`.

Как это проверить?