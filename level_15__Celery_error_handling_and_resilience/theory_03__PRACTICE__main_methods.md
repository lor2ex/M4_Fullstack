### 1. Структура проекта

`create_structure.py`

```python

from pathlib import Path

SPACES = 4  # Число пробелов на 1 уровень

tree = """
├── docker-compose.yml
├── celery_app.py
├── tasks/
│   ├── __init__.py
│   ├── task_retry.py               # ретраи и временные ошибки
│   ├── task_fatal.py               # фатальные ошибки
│   ├── task_idempotent.py          # идемпотентность
│   ├── task_timeout.py             # таймауты
│   ├── task_timeout_handled.py     # управляемые таймауты
│   └── task_logging.py             # наблюдаемость
└── runs/
    ├── run_retry.py
    ├── run_fatal.py
    ├── run_idempotent_once.py
    ├── run_idempotent_twice.py
    ├── run_timeout.py
    ├── run_timeout_handled.py
    └── run_logging.py
""".strip()
    
def create_structure(tree_text: str, root_dir: str = "."):
    root = Path(root_dir).resolve()
    stack = [root]

    for line in tree_text.splitlines():
        if not line.strip():
            continue

        # Считаем уровень вложенности по отступам (4 пробела = 1 уровень)
        stripped = line.lstrip(" │├─└")
        level = (len(line) - len(stripped)) // SPACES
        
        # Убираем комментарии
        stripped = stripped.split("#", 1)[0].rstrip()
        
        # Убираем префиксы веток
        name = stripped.lstrip(" ─└├│")

        if not name:
            continue

        # Возвращаемся на нужный уровень в стеке
        while len(stack) > level:
            stack.pop()

        current = stack[-1]
        path = current / name

        # Папка или файл?
        if name.endswith('/'):
            name = name.rstrip('/')
            path = current / name
            path.mkdir(parents=True, exist_ok=True)
            stack.append(path)
        else:
            # Файл
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.touch(exist_ok=True)
            symbol = "✓" if existed else "✓"

    print("\nСтруктура создана/проверена")


if __name__ == "__main__":
    print("Создание структуры проекта...\n")
    create_structure(tree)
```

#### Устанавливаем зависимости:

```bash
pip install celery[redis]

pip freeze > requirements.txt
```

---

### 2. Docker Compose с Redis

```yaml
services:
  redis:
    image: redis:7
    container_name: redis
    ports:
      - "6379:6379"
```
---

### 3. Базовое Celery-приложение

`celery_app.py`

```python
from celery import Celery


app = Celery(
    'celery_error_demo',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=[
        'tasks.task_retry',
        'tasks.task_fatal',
        'tasks.task_idempotent',
        'tasks.task_timeout',
        'tasks.task_logging',
        'tasks.task_timeout_handled',
    ]
)
```
---

### 4. Запускаем worker

```bash
celery -A celery_app worker --loglevel=info
```

---

### 5. Общие исключения

`tasks/__init__.py`

```python
class TemporaryError(Exception):
    """Временная ошибка — можно ретраить"""
    pass


class FatalError(Exception):
    """Фатальная ошибка — ретраи бессмысленны"""
    pass
```

---

### 6. Тест №1 — ретраи (TemporaryError)

#### Задача

`tasks/task_retry.py`

```python
from celery_app import app
from tasks import TemporaryError
import logging

logger = logging.getLogger(__name__)

@app.task(
    bind=True,
    autoretry_for=(TemporaryError,),
    retry_kwargs={'max_retries': 3, 'countdown': 1},
)
def retry_task(self, fail_until_attempt=2):
    attempt = self.request.retries + 1
    logger.info(f"[retry_task] attempt={attempt}")

    if attempt <= fail_until_attempt:
        raise TemporaryError("Временный сбой")

    return {
        "status": "success",
        "attempts": attempt
    }
```

#### Запуск

`runs/run_retry.py`

```python
from tasks.task_retry import retry_task
import time

res = retry_task.delay(fail_until_attempt=2)

while not res.ready():
    time.sleep(0.5)

print(res.get())
```

### Что видим?

* задача **падает → дважды ретраится → успешна**
* количество попыток совпадает с ожиданиями (2)

✔ Проверяет пункты:
**классификация ошибок + ретраи + ограничения**

```
[2026-02-12 23:05:54,119: INFO/MainProcess] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] received
[2026-02-12 23:05:54,120: INFO/ForkPoolWorker-8] [retry_task] attempt=1
[2026-02-12 23:05:54,132: INFO/MainProcess] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] received
[2026-02-12 23:05:54,138: INFO/ForkPoolWorker-8] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] retry: Retry in 1s: TemporaryError('Временный сбой')
[2026-02-12 23:05:55,125: INFO/ForkPoolWorker-8] [retry_task] attempt=2
[2026-02-12 23:05:55,130: INFO/MainProcess] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] received
[2026-02-12 23:05:55,133: INFO/ForkPoolWorker-8] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] retry: Retry in 1s: TemporaryError('Временный сбой')
[2026-02-12 23:05:56,129: INFO/ForkPoolWorker-8] [retry_task] attempt=3
[2026-02-12 23:05:56,132: INFO/ForkPoolWorker-8] Task tasks.task_retry.retry_task[18d8e33f-dff0-4ef2-8249-def23eda54d3] succeeded in 0.003124961000139592s: {'status': 'success', 'attempts': 3}
```

---

# TODO добавить предупреждение перегружать воркер после каждого добавления кода!!!


### 7. Тест №2 — фатальная ошибка (без ретраев)

#### Задача

`tasks/task_fatal.py`

```python
from celery_app import app
from tasks import FatalError

@app.task
def fatal_task():
    raise FatalError("Невосстановимая ошибка")
```

#### Запуск

`runs/run_fatal.py`

```python
from tasks.task_fatal import fatal_task
import time

res = fatal_task.delay()

while not res.ready():
    time.sleep(0.5)

try:
    res.get()
except Exception as e:
    print("FAILED:", type(e).__name__, e)
```

### Что видим?

* **нет ретраев**
* ошибка сразу финальная

✔ Проверяет пункт:
**разделение временных и логических ошибок**

```
[2026-02-12 23:09:43,677: ERROR/MainProcess] Received unregistered task of type 'tasks.task_fatal.fatal_task'.
The message has been ignored and discarded.                                                                                                                                                                                
                                                                                                                                                                                                                           
Did you remember to import the module containing this task?                                                                                                                                                                
Or maybe you're using relative imports?                                                                                                                                                                                    
                                                                                                                                                                                                                           
Please see                                                                                                                                                                                                                 
https://docs.celeryq.dev/en/latest/internals/protocol.html                                                                                                                                                                 
for more information.                                                                                                                                                                                                      
                                                                                                                                                                                                                           
The full contents of the message body was:                                                                                                                                                                                 
b'[[], {}, {"callbacks": null, "errbacks": null, "chain": null, "chord": null}]' (77b)                                                                                                                                     
                                                                                                                                                                                                                           
The full contents of the message headers:                                                                                                                                                                                  
{'lang': 'py', 'task': 'tasks.task_fatal.fatal_task', 'id': '36afd367-ad0f-41cb-83c5-1cceb04d35ac', 'shadow': None, 'eta': None, 'expires': None, 'group': None, 'group_index': None, 'retries': 0, 'timelimit': [None, None], 'root_id': '36afd367-ad0f-41cb-83c5-1cceb04d35ac', 'parent_id': None, 'argsrepr': '()', 'kwargsrepr': '{}', 'origin': 'gen16082@su-Aspire-A517-58M', 'ignore_result': False, 'replaced_task_nesting': 0, 'stamped_headers': None, 'stamps': {}}                                                                                                                                                                                                   
                                                                                                                                                                                                                           
The delivery info for this task is:                                                                                                                                                                                        
{'exchange': '', 'routing_key': 'celery'}                                                                                                                                                                                  
Traceback (most recent call last):                                                                                                                                                                                         
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/worker/consumer/consumer.py", line 668, in on_task_received                                               
    strategy = strategies[type_]                                                                                                                                                                                           
               ~~~~~~~~~~^^^^^^^                                                                                                                                                                                           
KeyError: 'tasks.task_fatal.fatal_task'                                                                                                                                                                                    

```
---

### 8. Тест №3 — идемпотентность (ключевая часть)

#### Задача

`tasks/task_idempotent.py`

```python
from celery_app import app
import logging

logger = logging.getLogger(__name__)

PROCESSED = set()

@app.task
def idempotent_task(item_id):
    if item_id in PROCESSED:
        logger.info(f"[item={item_id}] already processed")
        return "skipped"

    logger.info(f"[item={item_id}] processing")
    PROCESSED.add(item_id)
    return "done"
```

---

#### Первый запуск

`runs/run_idempotent_once.py`

```python
from tasks.task_idempotent import idempotent_task
print(idempotent_task.delay(42).get())
```

## Повторный запуск

`runs/run_idempotent_twice.py`

```python
from tasks.task_idempotent import idempotent_task
print(idempotent_task.delay(42).get())
```

### Что видим?

* первый запуск → `done`

```
[2026-02-12 23:20:46,693: INFO/MainProcess] Task tasks.task_idempotent.idempotent_task[b36d3a66-ef73-4ddb-968a-77e393e674a9] received
[2026-02-12 23:20:46,695: INFO/ForkPoolWorker-7] [item=42] processing
[2026-02-12 23:20:46,700: INFO/ForkPoolWorker-7] Task tasks.task_idempotent.idempotent_task[b36d3a66-ef73-4ddb-968a-77e393e674a9] succeeded in 0.0052137980001134565s: 'done'
```

* второй второй → `skipped`

```
[2026-02-12 23:22:49,116: INFO/MainProcess] Task tasks.task_idempotent.idempotent_task[31779038-bc9d-4e59-936f-640cccb1d8de] received
[2026-02-12 23:22:49,116: INFO/ForkPoolWorker-7] [item=42] already processed
[2026-02-12 23:22:49,117: INFO/ForkPoolWorker-7] Task tasks.task_idempotent.idempotent_task[31779038-bc9d-4e59-936f-640cccb1d8de] succeeded in 0.0008785590016486822s: 'skipped
```


* Таким образом идемпотентность успешно реализована: **повтор безопасен**

✔ Проверяет пункт:
**идемпотентность как обязательное свойство**

---

### 9. Тест №4 — таймауты

| Параметр          | Что это       | Как действует                          |
| ----------------- | ------------- | -------------------------------------- |
| `soft_time_limit` | Мягкий лимит  | Внутри задачи выбрасывается исключение |
| `time_limit`      | Жёсткий лимит | Процесс задачи **убивается**           |


#### Задача

`tasks/task_timeout.py`

```python
from celery_app import app
import time

@app.task(soft_time_limit=2, time_limit=5)
def slow_task():
    time.sleep(10)
    return "done"
```

#### Запуск

`runs/run_timeout.py`

```python
from tasks.task_timeout import slow_task
import time

res = slow_task.delay()

delay, start = 0, time.time()
while not res.ready():
    delay += 1
    print(f"Delay is {delay} sec.")
    time.sleep(delay)

try:
    res.get()
except Exception as e:
    end = time.time()
    print(f"Delay is {end - start:.2f} sec.")
    print("TIMEOUT:", type(e).__name__)

```

✔ Проверяет пункт:
**таймауты как элемент устойчивости**

**Логи воркера**:

```
[2026-02-13 13:02:19,950: INFO/MainProcess] Task tasks.task_timeout.slow_task[af26136d-df2d-4da8-841b-8ed63989548a] received
[2026-02-13 13:02:21,952: WARNING/MainProcess] Soft time limit (2s) exceeded for tasks.task_timeout.slow_task[af26136d-df2d-4da8-841b-8ed63989548a]
[2026-02-13 13:02:21,958: ERROR/ForkPoolWorker-8] Task tasks.task_timeout.slow_task[af26136d-df2d-4da8-841b-8ed63989548a] raised unexpected: SoftTimeLimitExceeded()
Traceback (most recent call last):                                                                                                                                                                                         
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/trace.py", line 479, in trace_task                                                                    
    R = retval = fun(*args, **kwargs)                                                                                                                                                                                      
                 ^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                                      
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/trace.py", line 779, in __protected_call__                                                            
    return self.run(*args, **kwargs)                                                                                                                                                                                       
           ^^^^^^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                                       
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/tasks/task_timeout.py", line 6, in slow_task                                                                                                        
    time.sleep(10)                                                                                                                                                                                                         
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/billiard/pool.py", line 228, in soft_timeout_sighandler                                                          
    raise SoftTimeLimitExceeded()                                                                                                                                                                                          
billiard.exceptions.SoftTimeLimitExceeded: SoftTimeLimitExceeded()  
```

**Логи запускающего скрипта**:

```
/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/bin/python3.12 /home/su/LearningProjects/celery-error-handling-and-resilience/runs/run_timeout.py 
Delay is 1.0 sec.
Delay is 2.0 sec.
TIMEOUT: SoftTimeLimitExceeded

Process finished with exit code 0
```

### Таким образом

* Через 2 секунды после запуска в процессе задачи выбрасывается `SoftTimeLimitExceeded`.
* Так как исключение не обработано, задача немедленно завершается с ошибкой 
  `billiard.exceptions.SoftTimeLimitExceeded: SoftTimeLimitExceeded() `
* Процесс воркера освобождается сразу и готов принимать новые задачи.
* Жёсткий таймаут (time_limit=5) не срабатывает, потому что к этому моменту задача уже завершена.
* Жёсткий таймаут используется как защита на случай, если задача не реагирует на soft timeout.
---

### 10. Тест №5 — управляемый таймаут

#### Задача

`tasks/task_timeout_handled.py.py`

```python
from celery_app import app
from celery.exceptions import SoftTimeLimitExceeded
import time
import logging

logger = logging.getLogger(__name__)

@app.task(
    bind=True,
    soft_time_limit=3,
    time_limit=6,
)
def slow_task_with_cleanup(self):
    logger.info("START task")

    try:
        for i in range(10):
            logger.info(f"working... step={i}")
            time.sleep(1)

    except SoftTimeLimitExceeded:
        logger.warning("SOFT TIMEOUT caught — cleaning up")
        # здесь могла бы быть:
        # - запись статуса в БД
        # - rollback транзакции
        # - освобождение ресурсов
        return {
            "status": "soft_timeout",
            "step": i,
        }

    logger.info("FINISH task normally")
    return {
        "status": "done"
    }

```


**Что здесь принципиально иное?**

1. Цикл вместо `sleep(10)`
    ```
    for i in range(10):
        time.sleep(1)
    ```
    
    Это позволяет:

   * увидеть, на каком шаге произошёл таймаут
   * продемонстрировать, что задача что-то делала, а не просто «висела»

2. Явный `except SoftTimeLimitExceeded`  

   Это ключевой момент всей демонстрации, поскольку мы:

   * НЕ даём задаче «упасть»
   * НЕ доводим дело до time_limit
   * сами решаем, как она завершится


#### Запуск

`runs/run_timeout_handled.py.py`

```python
from tasks.task_timeout_handled import slow_task_with_cleanup
import time

res = slow_task_with_cleanup.delay()

while not res.ready():
    time.sleep(0.5)

print("RESULT:", res.get())


```

✔ Проверяет пункт:
**таймауты как элемент устойчивости**

**Логи воркера**:

```
[2026-02-13 14:43:22,324: INFO/MainProcess] Task tasks.task_timeout_handled.slow_task_with_cleanup[16970492-3440-4038-8160-79c0bd05faf6] received
[2026-02-13 14:43:22,325: INFO/ForkPoolWorker-7] START task
[2026-02-13 14:43:22,325: INFO/ForkPoolWorker-7] working... step=0
[2026-02-13 14:43:23,326: INFO/ForkPoolWorker-7] working... step=1
[2026-02-13 14:43:24,326: INFO/ForkPoolWorker-7] working... step=2
[2026-02-13 14:43:25,326: INFO/ForkPoolWorker-7] working... step=3
[2026-02-13 14:43:25,327: WARNING/MainProcess] Soft time limit (3s) exceeded for tasks.task_timeout_handled.slow_task_with_cleanup[16970492-3440-4038-8160-79c0bd05faf6]
[2026-02-13 14:43:25,327: WARNING/ForkPoolWorker-7] SOFT TIMEOUT caught — cleaning up
[2026-02-13 14:43:25,328: INFO/ForkPoolWorker-7] Task tasks.task_timeout_handled.slow_task_with_cleanup[16970492-3440-4038-8160-79c0bd05faf6] succeeded in 3.003358543000104s: {'status': 'soft_timeout', 'step': 3}
```
**Как видим**:

* задача не убита
* лог завершения есть
* `hard timeout` не понадобился

**Логи запускающего скрипта**:

```
/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/bin/python3.12 /home/su/LearningProjects/celery-error-handling-and-resilience/runs/run_timeout_handled.py 
RESULT: {'status': 'soft_timeout', 'step': 3}

Process finished with exit code 0
```

**То есть**:

* задача контролируемо завершилась
* результат предсказуем 
* состояние известно