В контексте устойчивости асинхронных систем логирование отвечает за:

* понимание **что именно произошло**
* различие:

  * ошибка
  * retry
  * soft timeout
  * fatal failure
* восстановление цепочки событий **после факта**

Без логирования *все остальные механизмы почти бесполезны*.

---

### Ответы на какие вопросы должно демонстрировать логирование?

1. что задача **началась**
2. сколько раз она **ретраилась**
3. чем она **закончилась**
4. что именно было причиной сбоя

И всё это — **явно и читаемо**.

---


#### Задача

**Явное логирование жизненного цикла задачи**

`tasks/task_logging.py`

```python
from celery_app import app
from celery.exceptions import SoftTimeLimitExceeded
import logging
import time

logger = logging.getLogger(__name__)

@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 1},
)
def logged_task(self, fail_at_step=2):
    task_id = self.request.id
    attempt = self.request.retries + 1

    logger.info(
        f"[task={task_id}] START attempt={attempt}"
    )

    try:
        for step in range(5):
            logger.info(
                f"[task={task_id}] step={step}"
            )
            time.sleep(1)

            if step == fail_at_step:
                raise RuntimeError("Simulated failure")

    except SoftTimeLimitExceeded:
        logger.warning(
            f"[task={task_id}] SOFT TIMEOUT"
        )
        raise

    except Exception as exc:
        logger.error(
            f"[task={task_id}] ERROR: {exc}"
        )
        raise exc

    logger.info(
        f"[task={task_id}] SUCCESS"
    )

    return {
        "status": "done",
        "attempts": attempt,
    }
```

* `max_retries` — сколько раз можно попробовать ещё.
* `countdown` — через сколько попробовать снова.

---

### Запуск

`runs/run_logging.py`

```python
from tasks.task_logging import logged_task
import time

res = logged_task.delay(fail_at_step=1)

while not res.ready():
    time.sleep(0.5)

print(res.get())
```
---

#### Что этот пример демонстрирует?

В нашем случае задача всегда гарантированно падает на 3-м шаге:  
```python
            if step == fail_at_step:
                raise RuntimeError("Simulated failure")
```

Так что, этот пример - отличная иллюстрация факта, что ретраи не исправляют ошибка сами по себе!  
Максимум, на что они способны - запустить ещё раз в надежде, что изменятся внешние условия.


**Логи воркера**:

```text
[2026-02-13 15:03:53,307: INFO/MainProcess] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] received
[2026-02-13 15:03:53,309: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] START attempt=1
[2026-02-13 15:03:53,309: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=0
[2026-02-13 15:03:54,309: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=1
[2026-02-13 15:03:55,310: ERROR/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] ERROR: Simulated failure
[2026-02-13 15:03:55,320: INFO/MainProcess] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] received
[2026-02-13 15:03:55,325: INFO/ForkPoolWorker-7] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] retry: Retry in 1s: RuntimeError('Simulated failure')
[2026-02-13 15:03:56,314: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] START attempt=2
[2026-02-13 15:03:56,314: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=0
[2026-02-13 15:03:57,314: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=1
[2026-02-13 15:03:58,314: ERROR/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] ERROR: Simulated failure
[2026-02-13 15:03:58,320: INFO/MainProcess] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] received
[2026-02-13 15:03:58,323: INFO/ForkPoolWorker-7] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] retry: Retry in 1s: RuntimeError('Simulated failure')
[2026-02-13 15:03:59,317: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] START attempt=3
[2026-02-13 15:03:59,317: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=0
[2026-02-13 15:04:00,317: INFO/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] step=1
[2026-02-13 15:04:01,318: ERROR/ForkPoolWorker-7] [task=7c6c9352-4010-4925-8cdd-58343d6fe0e2] ERROR: Simulated failure
[2026-02-13 15:04:01,324: ERROR/ForkPoolWorker-7] Task tasks.task_logging.logged_task[7c6c9352-4010-4925-8cdd-58343d6fe0e2] raised unexpected: RuntimeError('Simulated failure')
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
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/tasks/task_logging.py", line 41, in logged_task                                                                                                     
    raise exc                                                                                                                                                                                                              
  File "/home/su/LearningProjects/celery-error-handling-and-resilience/tasks/task_logging.py", line 29, in logged_task                                                                                                     
    raise RuntimeError("Simulated failure")                                                                                                                                                                                
RuntimeError: Simulated failure                
```

**Это идеальный пример логирования**, потому что:

* `retry` явно виден
* причина `retry` ясна
* финальный статус очевиден

---

### Важное архитектурное замечание

❗ **Логирование — не замена мониторингу**

Но без логирования:

* невозможно понять, *почему* мониторинг сработал
* невозможно восстановить контекст ошибки

---

