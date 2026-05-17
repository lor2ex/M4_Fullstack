## ⚠️ ВАЖНЫЕ исправление предыдущих ошибок ❗

### 1. Исправление истории постов

#### 1.1. `app/tasks/generate.py`

**Предыдущая версия**

```python
        content_hash = hashlib.md5(
            f"{title}{summary}{published_at_str}".encode()
        ).hexdigest()[:16]

        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

```

**Исправленная версия**

1. Убираем `{published_at_str}`
2. Добавляем защиту от повторной генерации


```python
        content_hash = hashlib.md5(
            f"{title}{summary}".encode()
        ).hexdigest()[:16]

        generated_key = f"{GENERATED_PREFIX}:{source}:{content_hash}"

        # Добавляем защиту от повторной генерации
        if redis.exists(generated_key):
            logger.info(f"Пост уже был сгенерирован ранее → {generated_key}")
            return 1    
```

#### 1.2. `app/tasks/filter.py`

**Предыдущая версия**

```python
            filtered_key = f"news:filtered:{source}:{published_at}"
```

**Исправленная версия**

```python
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]   # тот же хеш
            filtered_key = f"news:filtered:{source}:{content_hash}"
```

#### 1.3. `app/tasks/filter.py`

**Предыдущая версия**

```python
            # --- дедупликация по хешу ---
            hash_digest = hashlib.md5(content.encode()).hexdigest()
            dup_key = f"news:dup:{hash_digest}"

```

**Исправленная версия**

```python
            # --- дедупликация по хешу ---
            hash_digest = hashlib.md5(content.encode()).hexdigest()[:16]   # [:16] для единообразия
            dup_key = f"news:dup:{hash_digest}"

```


#### 1.4. `app/tasks/generate.py`

Удаляем отфильтрованные новости.

В текущей архитектуре не была учтена проверка:
* "Была ли отфильтрованная новость сгенерирована ранее".

Результат:
* Отфильтрованные новости генерируются до тех пор, пока не истечёт их время жизни в Redis.

Решение:
* Удаляем отфильтрованную новость сразу после генерации.

**Предыдущая версия**
```python
        redis.expire(generated_key, GENERATED_TTL)

        logger.info(f"Сгенерированный пост сохранён → {generated_key}")
```

**Исправленная версия**

```python
        redis.expire(generated_key, GENERATED_TTL)
        deleted = redis.delete(filtered_key)
        logger.info(f"Сгенерированный пост сохранён → {generated_key} | filtered удалён: {deleted}")
```