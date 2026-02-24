Давайте дополним предыдущий проект. 
И проверим, как разные типы задач (CPU или I/O) выполняются воркерами с разными типами асинхронности.

### 1. В `tasks.py` добавим новые задачи:


```python
@app.task
def heavy_io_task(x):
    """
    Задача, которая занимает 1 секунду
    (долгая IO задача)
    """
    time.sleep(1)
    return x * x


def primes_up_to(n):
    """
    Находит все простые числа до n простым способом
    (долгая CPU задача)
    """
    primes = []
    for i in range(2, n + 1):
        is_prime = True
        for p in primes:
            if p * p > i:
                break
            if i % p == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(i)
    return primes

@app.task
def heavy_cpu_task(n):
    return len(primes_up_to(n))
```

### 2. `compare_io_tasks.py`

Запуск нескольких IO задач по отправке пакета email или парсинга сайтов.

```python
import time
from celery import group
from celery.result import GroupResult
from tasks import heavy_io_task

TASK_COUNT = 1000
START = time.time()

print(f"Тест: {TASK_COUNT} I/O-задач")

start = time.perf_counter()

job = group(heavy_io_task.s(i) for i in range(1, TASK_COUNT + 1))
result: GroupResult = job.apply_async()          # отправляем группу асинхронно

print(f"Группа из {TASK_COUNT} задач запущена (id: {result.id})")

# блокируем дальнейшее выполнение, пока не дождёмся выполнения всех отправленных задач
results = result.get()

print(f"Группа из {TASK_COUNT} задач выполнена за {time.time()-START:.2f} сек")

# Поочерёдно запускаем workers и сравниваем (лучше записываем) результат:

# celery -A celery_app worker -Q default --pool=gevent --concurrency=1000 -l info       2.79
# celery -A celery_app worker -Q default --pool=threads --concurrency=1000 -l info      5.36
# celery -A celery_app worker -Q default --pool=prefork --concurrency=16 -l info       63.60
```

### 3. `compare_cpu_tasks.py`

Запуск нескольких сложных вычислительных задач.

```python
import time
from celery import group
from celery.result import GroupResult
from tasks import heavy_cpu_task

N = 500_000  # предел для вычисления простых чисел
TASK_COUNT = 200
START = time.time()

print(f"Тест: {TASK_COUNT} CPU-задач")

start = time.perf_counter()

job = group(heavy_cpu_task.s(N) for _ in range(1, TASK_COUNT + 1))
result: GroupResult = job.apply_async()          # отправляем группу асинхронно

print(f"Группа из {TASK_COUNT} задач запущена (id: {result.id})")

# Вариант 1: блокирующее ожидание всех результатов
results = result.get()                           # ждёт все задачи, возвращает список результатов

print(f"Группа из {TASK_COUNT} задач выполнена за {time.time()-START:.2f} сек")

# Поочерёдно запускаем workers и сравниваем (лучше записываем) результат:

# celery -A celery_app worker -Q default --pool=gevent --concurrency=200 -l info        40.38
# celery -A celery_app worker -Q default --pool=threads --concurrency=200 -l info       51.39
# celery -A celery_app worker -Q default --pool=prefork --concurrency=4 -l info         14.36
```

### 4. Практическая работа

Поочерёдно запускаем соответствующий воркет и проверяем время выполнения.

Сначала для I/O-задач `compare_io_tasks.py`:

```bash
celery -A celery_app worker -Q default --pool=gevent --concurrency=1000 -l info  
celery -A celery_app worker -Q default --pool=threads --concurrency=1000 -l info     
celery -A celery_app worker -Q default --pool=prefork --concurrency=16 -l info 
```

А затем для CPU-задач `compare_io_tasks.py`:

```bash
celery -A celery_app worker -Q default --pool=gevent --concurrency=200 -l info  
celery -A celery_app worker -Q default --pool=threads --concurrency=200 -l info     
celery -A celery_app worker -Q default --pool=prefork --concurrency=4 -l info 
```

### 5. Выводы

Для CPU задач лучше всего показали себя `prefork`-воркеры (истинный параллелизм).  
Для I/O задач лучше использовать concurrency асинхронность (квази-параллелизм).  
Кооперативная многозадачность в обоих случаях показывает немного лучший результат, чем потоки.