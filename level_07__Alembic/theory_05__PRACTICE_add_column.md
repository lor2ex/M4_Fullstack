## Добавление новой колонки и заполнение её данными

1. Добавляет колонку `city` в таблицу `user`.
2. Заполняет её данными для существующих пользователей.

---

### 1. Создаём новую миграцию

```bash
alembic revision -m "add city column to user"
```

Alembic создаст файл в `versions/` с новым `revision id`.

---

### 2. Пишем код миграции

В созданную миграцию добавляем функции добавления и отката данных

```python
def upgrade() -> None:
    # 1. Добавляем новую колонку city
    op.add_column('user', sa.Column('city', sa.String(), nullable=True))

    # 2. Заполняем данные для существующих пользователей
    op.execute("""
        UPDATE "user"
        SET city = CASE id
            WHEN 1 THEN 'New York'
            WHEN 2 THEN 'Los Angeles'
            WHEN 3 THEN 'Chicago'
            WHEN 4 THEN 'Houston'
            WHEN 5 THEN 'Miami'
        END
    """)

def downgrade() -> None:
    # Удаляем колонку city при откате миграции
    op.drop_column('user', 'city')
```

---

**Что делает эта миграция**

1. `op.add_column()` — добавляет колонку `city` в таблицу `user`.
2. `op.execute()` с `UPDATE ... CASE` — заполняет существующие строки значениями.
3. `op.drop_column('user', 'city')` — удаляет колонку, чтобы откат миграции был чистым.

---

### 3. Применяем миграцию

```bash
alembic upgrade head
```

Результат выполнения команды:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 58c4fd1c59b4 -> 3b3bc4b2d744, add city column to user
```

---

### 4. Проверяем изменения в таблицу

```
Найдено таблиц: ['alembic_version', 'user']

Содержимое таблицы 'alembic_version':
{'version_num': '3b3bc4b2d744'}

Содержимое таблицы 'user':
{'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com', 'city': 'New York'}
{'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com', 'city': 'Los Angeles'}
{'id': 3, 'name': 'Charlie', 'age': 22, 'email': 'charlie@example.com', 'city': 'Chicago'}
{'id': 4, 'name': 'Diana', 'age': 28, 'email': 'diana@example.com', 'city': 'Houston'}
{'id': 5, 'name': 'Eve', 'age': 35, 'email': 'eve@example.com', 'city': 'Miami'}
```


