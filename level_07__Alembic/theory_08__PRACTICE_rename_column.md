### Переименование столбца

Переименование `city` → `address` с помощью Alembic

**Исходное состояние**

В таблице `"user"` есть колонка:

```
city VARCHAR(100)
```

Нужно получить:

```
address VARCHAR(100)
```

без потери данных.

---

### 1. Создаём новую миграцию

```bash
alembic revision -m "rename city to address"
```

---

### 2. Изменяем функции `upgrade()` и `downgrade()`

Правильный способ: `op.alter_column(..., new_column_name=...)`

```python
def upgrade() -> None:
    op.alter_column(
        'user',
        'city',
        new_column_name='address',
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'user',
        'address',
        new_column_name='city',
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )
```
где

* `'user'` — имя таблицы 
* `'city'` / `'address'` — текущее имя колонки
* `new_column_name`— новое имя
* `existing_type` — **обязателен** для PostgreSQL
* `existing_nullable` — фиксируем NULL-состояние

**Тип НЕ меняется**, поэтому `type_` не используется.

---

## 3. Какой SQL реально выполнится (PostgreSQL)

```bash
alembic upgrade head --sql
```
Alembic сгенерирует:

```sql
ALTER TABLE "user" ALTER COLUMN city TYPE VARCHAR(100);
```

---

### 4. Применяем миграцию

```bash
alembic upgrade head
```

Ожидаемый лог:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 1ee2a1d447d3 -> 7dbf62d63b1a, rename city to address```
```
---

### 5. Проверяем результат

**`./main.py`**

```
Найдено таблиц: ['alembic_version', 'user']

Содержимое таблицы 'alembic_version':
{'version_num': '403fdd0f81d9'}

Содержимое таблицы 'user':
{'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com', 'address': 'New York'}
{'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com', 'address': 'Los Angeles'}
{'id': 3, 'name': 'Charlie', 'age': 22, 'email': 'charlie@example.com', 'address': 'Chicago'}
{'id': 4, 'name': 'Diana', 'age': 28, 'email': 'diana@example.com', 'address': 'Houston'}
{'id': 5, 'name': 'Eve', 'age': 35, 'email': 'eve@example.com', 'address': 'Miami'}
```

---

⚠️⚠️⚠️⚠️⚠️
## 6. Важный практический момент (ORM)
❗ ❗ ❗ ❗ ❗     

После миграции **обязательно обновляем модель модель**,
если изменения делаем вручную:

```python
class User(Base):
    address: Mapped[str] = mapped_column(String(100), nullable=True)
```

Иначе ORM и БД разъедутся.

---

### Шпаргалки изменений столбца

| Задача            | Alembic-операция                    |
| ----------------- | ----------------------------------- |
| Изменить тип      | `alter_column(type_)`               |
| Изменить nullable | `alter_column(nullable=...)`        |
| Переименовать     | `alter_column(new_column_name=...)` |
| Удалить           | `drop_column`                       |
| Добавить          | `add_column`                        |

