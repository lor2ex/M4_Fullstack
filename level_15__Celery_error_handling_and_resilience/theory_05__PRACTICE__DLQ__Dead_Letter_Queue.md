### Идея DLQ в Celery

Celery **не имеет DLQ “из коробки”**, как RabbitMQ.
DLQ реализуется **логически**, обычно одним из способов:

1. отдельная очередь (`failed_tasks`)
2. отдельная задача-обработчик
3. сохранение контекста ошибки (`task_id`, `args`, `traceback`)

---

### 1. Добавляем очереди в конфигурацию

## `celery_app.py`

```python
from celery import Celery
from kombu import Queue, Exchange

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
        # --- new tasks ---
        'tasks.task_dlq',
        'tasks.task_with_dlq',
    ]
)

dead_letter_exchange = Exchange('dead_letter', type='direct')

app.conf.task_queues = (
    Queue('default'),
    Queue('dead_letter', exchange=dead_letter_exchange, routing_key='dead_letter'),
)

app.conf.task_default_queue = 'default'

```

---

### 2. DLQ-задача (приёмник «мертвых» задач)

**`tasks/task_dlq.py`**

```python
from celery_app import app
import logging

logger = logging.getLogger(__name__)

@app.task
def dead_letter_handler(payload):
    logger.error("DLQ MESSAGE RECEIVED")
    logger.error(payload)
```

Это **не retry**, а **финальная точка**.

---

### 3. Основная задача с retry и отправкой в DLQ

**`tasks/task_with_dlq.py`**

```python
from celery_app import app
from celery.exceptions import MaxRetriesExceededError
import logging

logger = logging.getLogger(__name__)

@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 1},
)
def fragile_task(self, value):
    try:
        logger.info(f"Processing value={value}")
        raise RuntimeError("Always fails")

    except MaxRetriesExceededError:
        # сюда мы почти не попадём, но оставим для ясности
        raise

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error("Retries exhausted → sending to DLQ")

            from tasks.task_dlq import dead_letter_handler

            dead_letter_handler.apply_async(
                kwargs={
                    "payload": {
                        "task": self.name,
                        "task_id": self.request.id,
                        "args": self.request.args,
                        "kwargs": self.request.kwargs,
                        "error": str(exc),
                        "retries": self.request.retries,
                    }
                },
                queue='dead_letter',
            )

            raise  # фиксируем FAILED

        raise self.retry(exc=exc, countdown=10)
```

---

### 4. Запуск воркеров

#### Основной воркер

```bash
celery -A celery_app.app worker -Q default --loglevel=info
```

#### DLQ воркер (отдельный!)

```bash
celery -A celery_app.app worker -Q dead_letter --loglevel=info
```

⚠️ **Это принципиально важно**:
DLQ **не должна мешать основной очереди**❗

---

### 5. Скрипт запуска

**`runs/run_dlq.py`**

```python
from tasks.task_with_dlq import fragile_task
import time

res = fragile_task.delay(123)

while not res.ready():
    time.sleep(0.5)

try:
    res.get()
except Exception:
    print("Task failed and sent to DLQ")
```

---

### 6. Что видим?

#### В основном воркере

```
[2026-02-13 16:48:26,390: INFO/MainProcess] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] received
[2026-02-13 16:48:26,391: INFO/ForkPoolWorker-7] Processing value=123
[2026-02-13 16:48:26,401: INFO/MainProcess] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] received
[2026-02-13 16:48:26,405: INFO/ForkPoolWorker-7] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] retry: Retry in 10s: RuntimeError('Always fails')
[2026-02-13 16:48:36,395: INFO/ForkPoolWorker-7] Processing value=123
[2026-02-13 16:48:36,399: INFO/MainProcess] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] received
[2026-02-13 16:48:36,403: INFO/ForkPoolWorker-7] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] retry: Retry in 10s: RuntimeError('Always fails')
[2026-02-13 16:48:46,398: INFO/ForkPoolWorker-7] Processing value=123
[2026-02-13 16:48:46,402: INFO/MainProcess] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] received
[2026-02-13 16:48:46,405: INFO/ForkPoolWorker-7] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] retry: Retry in 10s: RuntimeError('Always fails')
[2026-02-13 16:48:56,402: INFO/ForkPoolWorker-7] Processing value=123
[2026-02-13 16:48:56,402: ERROR/ForkPoolWorker-7] Retries exhausted → sending to DLQ
[2026-02-13 16:48:56,412: ERROR/ForkPoolWorker-7] Task tasks.task_with_dlq.fragile_task[25b55c51-09be-422b-901d-72cb89e734cb] raised unexpected: RuntimeError('Always fails')
Traceback (most recent call last):                                                                                                                                                                                         
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/trace.py", line 479, in trace_task                                                                    
    R = retval = fun(*args, **kwargs)                                                                                                                                                                                      
                 ^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                                      
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/trace.py", line 779, in __protected_call__                                                            
    return self.run(*args, **kwargs)                                                                                                                                                                                       
           ^^^^^^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                                       
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/autoretry.py", line 60, in run                                                                        
    ret = task.retry(exc=exc, **retry_kwargs)                                                                                                                                                                              
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                              
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/task.py", line 750, in retry                                                                          
    raise_with_context(exc)                                                                                                                                                                                                
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/.venv/lib/python3.12/site-packages/celery/app/autoretry.py", line 38, in run                                                                        
    return task._orig_run(*args, **kwargs)                                                                                                                                                                                 
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                                                                                                                                                 
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/tasks/task_with_dlq.py", line 15, in fragile_task                                                                                                   
    raise RuntimeError("Always fails")                                                                                                                                                                                     
RuntimeError: Always fails                      
```

После 3-х повторов задача окончательно упала.
Основной воркер готов к приёму новых задач.

---

#### В DLQ воркере

```text
[2026-02-13 16:48:56,410: INFO/MainProcess] Task tasks.task_dlq.dead_letter_handler[6d9e3bb8-417d-4ef8-90c9-763d17c8e784] received
[2026-02-13 16:48:56,411: ERROR/ForkPoolWorker-8] DLQ MESSAGE RECEIVED
[2026-02-13 16:48:56,412: ERROR/ForkPoolWorker-8] {'task': 'tasks.task_with_dlq.fragile_task', 'task_id': '25b55c51-09be-422b-901d-72cb89e734cb', 'args': [123], 'kwargs': {}, 'error': 'Always fails', 'retries': 3}
[2026-02-13 16:48:56,419: INFO/ForkPoolWorker-8] Task tasks.task_dlq.dead_letter_handler[6d9e3bb8-417d-4ef8-90c9-763d17c8e784] succeeded in 0.008030588000110583s: None
```

**Задача не потерялась**:
* Сразу после падения в `16:48:56` она перемистилась в воркер мёртвых задача.
* Контекст сохранён: 
  
    ```
    {
      'task': 'tasks.task_with_dlq.fragile_task', 
      'task_id': '25b55c51-09be-422b-901d-72cb89e734cb', 
      'args': [123], 
      'kwargs': {}, 
      'error': 'Always fails', 
      'retries': 3
    }
    ```

#### В терминале скрипта запуска:

```
Task failed and sent to DLQ
```

---

### 7. Подводим итоги

#### 7.1. Почему это «правильный» способ организации `DLQ`?

1. задача **не исчезает**
2. `retry` **ограничен**
3. `DLQ` **изолирована**
4. есть **полный контекст ошибки** 
5. можно:

   * анализировать ошибки
   * повторно запускать код
   * принимать меры по исправлению кода

---

#### 7.2. Как не стоит организовывать `DLQ`?

❌ Делать `DLQ` как `autoretry_for=(Exception,)` без лимитов  
❌ Писать в `DLQ` **на каждый retry**  
❌ Класть `DLQ` в ту же очередь  

---

#### 7.3. Самый важный вывод

> **DLQ — это не “очередь ошибок”,
> а место, куда задачи попадают *после исчерпания всех шансов*.**

---

