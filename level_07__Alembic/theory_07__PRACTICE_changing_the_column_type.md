### Изменение типа данных столбца

В последней миграции был создан столбец

```sql
ALTER TABLE "user" ADD COLUMN city VARCHAR;
```

Изменим тип данных столбца `city` с `VARCHAR` на `VARCHAR(100)`.


### 1. Создаём новую миграцию

```bash
alembic revision -m "change city column type"
```

---

### 2. Изменяем тип столбца в миграции

Изменяем дефолтное содержимое функций ` upgrade()` и `downgrade()`в миграции:

```python
def upgrade() -> None:
    op.alter_column(
        'user',
        'city',
        existing_type=sa.String(),
        type_=sa.String(length=100),
        existing_nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        'user',
        'city',
        existing_type=sa.String(length=100),
        type_=sa.String(),
        existing_nullable=True
    )
```

В обоих случаях:

`'user'` - имя таблицы
`'city'` - имя колонки
`existing_type` - существующей тип данных (ДО изменения)
`type_` - планируемый тип данных (ПОСЛЕ изменения)
`existing_nullable` - значения `NULL` остаются без изменения


---

### 3. Применяем миграцию

```bash
alembic upgrade head
```

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 3b3bc4b2d744 -> 1ee2a1d447d3, change city column type
```

---


### 4. Проверяем результат

Запускаем `./main.py`

```
Найдено таблиц: ['alembic_version', 'user']

Содержимое таблицы 'alembic_version':
{'version_num': '1ee2a1d447d3'}

Содержимое таблицы 'user':
{'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com', 'city': 'New York'}
{'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com', 'city': 'Los Angeles'}
{'id': 3, 'name': 'Charlie', 'age': 22, 'email': 'charlie@example.com', 'city': 'Chicago'}
{'id': 4, 'name': 'Diana', 'age': 28, 'email': 'diana@example.com', 'city': 'Houston'}
{'id': 5, 'name': 'Eve', 'age': 35, 'email': 'eve@example.com', 'city': 'Miami'}
```

---

### 5. ⚠️ ВАЖНО использовать только те изменения типов данных, которые не вызовут конфликта!

В противном случае — миграция просто упадёт ❌
