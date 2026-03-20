## Создание данных с помощью миграций

### 1. Создаём новую миграцию

В терминале, в папке проекта с Alembic, выполняем:

```bash
alembic revision -m "insert initial users"
```

* `-m` — это сообщение миграции, здесь `"insert initial users"`.
* После выполнения Alembic создаст файл миграции в папке `versions`, что-то вроде:
  `versions/abcd1234_insert_initial_users.py`.


В результате получаем файл миграции `xxxxx_insert_initial_users.py`:

```python
"""Revises: ce973c8f81fd
Create Date: 2025-12-16 01:51:35.797755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c4fd1c59b4'
down_revision: Union[str, Sequence[str], None] = 'ce973c8f81fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

```

---

### 2. Заполнение файла миграции

Наша задача: 
* заполнить функцию изменения `upgrade()` для добавления данных
* и сразу же заполнить функцию отката `downgrade()`, если потребуется удалить добавленные данные

Иными словами: 
* пишем код вставки 5 строк в таблицу в `upgrade()`
* и код удаления этих же строк в `downgrade()`



```python
def upgrade() -> None:
    # Вставка 5 пользователей в таблицу user
    op.bulk_insert(
        sa.table(
            'user',
            sa.column('id', sa.Integer),
            sa.column('name', sa.String),
            sa.column('age', sa.Integer),
            sa.column('email', sa.String)
        ),
        [
            {'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com'},
            {'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com'},
            {'id': 3, 'name': 'Charlie', 'age': 22, 'email': 'charlie@example.com'},
            {'id': 4, 'name': 'Diana', 'age': 28, 'email': 'diana@example.com'},
            {'id': 5, 'name': 'Eve', 'age': 35, 'email': 'eve@example.com'},
        ]
    )

def downgrade() -> None:
    # Удаляем эти записи при откате миграции
    op.execute(
        "DELETE FROM user WHERE id IN (1, 2, 3, 4, 5)"
    )
```

---

### 3. Применяем миграцию

В терминале выполняем:

```bash
alembic upgrade head
```

* Это применит все новые миграции, включая нашу вставку данных.
* Таблица `user` будет заполнена 5 пользователями.

Результат выполнения:

```bash
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ce973c8f81fd -> 58c4fd1c59b4, insert initial users
```

---

### 4. Проверяем результат

#### 4.1. Создадим файл `main.py` для вывода содержимого БД:

```python
import asyncio
from sqlalchemy import text, inspect

from database import engine


async def print_db_tables():

    async with engine.connect() as conn:

        async with engine.connect() as conn:  
            # Получаем список таблиц через run_sync
            def get_tables(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names()

            tables = await conn.run_sync(get_tables)
            print(f"Найдено таблиц: {tables}")

            for table in tables:
                print(f"\nСодержимое таблицы '{table}':")
                result = await conn.execute(text(f'SELECT * FROM "{table}"'))
                rows = result.all()  # <-- просто .all(), без await

                if rows:
                    for row in rows:
                        print(dict(row._mapping))
                else:
                    print("Таблица пуста.")

    await engine.dispose()



if __name__ == "__main__":
    asyncio.run(print_db_tables())

```

#### 4.2. Запускаем `main.py`

Результат выполнения:

```
Найдено таблиц: ['alembic_version', 'user']

Содержимое таблицы 'alembic_version':
{'version_num': '58c4fd1c59b4'}

Содержимое таблицы 'user':
{'id': 1, 'name': 'Alice', 'age': 25, 'email': 'alice@example.com'}
{'id': 2, 'name': 'Bob', 'age': 30, 'email': 'bob@example.com'}
{'id': 3, 'name': 'Charlie', 'age': 22, 'email': 'charlie@example.com'}
{'id': 4, 'name': 'Diana', 'age': 28, 'email': 'diana@example.com'}
{'id': 5, 'name': 'Eve', 'age': 35, 'email': 'eve@example.com'}

```