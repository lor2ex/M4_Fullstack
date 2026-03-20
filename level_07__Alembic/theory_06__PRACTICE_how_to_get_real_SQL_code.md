### 1. Как получить реальный SQL код миграции?

Alembic нигде не хранит миграции в реальном формате SQL.

Но их всегда можно посмотреть с помощью команды:

```bash
alembic upgrade head --sql
```

В этом случае вместо реального проведения миграции мы увидим её SQL-код:

```sql
INFO  [alembic.runtime.migration] Running upgrade 58c4fd1c59b4 -> 3b3bc4b2d744, add city column to user
-- Running upgrade 58c4fd1c59b4 -> 3b3bc4b2d744

ALTER TABLE "user" ADD COLUMN city VARCHAR;

UPDATE "user"
        SET city = CASE id
            WHEN 1 THEN 'New York'
            WHEN 2 THEN 'Los Angeles'
            WHEN 3 THEN 'Chicago'
            WHEN 4 THEN 'Houston'
            WHEN 5 THEN 'Miami'
        END;

UPDATE alembic_version SET version_num='3b3bc4b2d744' WHERE alembic_version.version_num = '58c4fd1c59b4';

COMMIT;

```


### 1. Получить SQL-код от самой первой до конкретной миграции ВКЛЮЧИТЕЛЬНО

```bash
alembic upgrade ce973c8f81fd --sql
```

➡ покажет SQL **до этой ревизии включительно**

---

### 2. SQL только для ДИАПАЗОНЕ миграций (или для ОДНОЙ НЕ последней миграции)

**Синтаксис `from:to`**

```bash
alembic upgrade ce973c8f81fd:58c4fd1c59b4 --sql
```

Где:

* `ce973c8f81fd` — предыдущая миграция
* `58c4fd1c59b4` — нужная миграция

➡ Alembic выведет **SQL только для этой миграции**

---

### 3. SQL для downgrade (откат)

```bash
alembic downgrade ce973c8f81fd --sql
```

или диапазон:

```bash
alembic downgrade 58c4fd1c59b4:ce973c8f81fd --sql
```

---

## 4. Узнать нужные revision id

```bash
alembic history
```
Эта команда выводит все миграции в хронологическом порядке:

```
1ee2a1d447d3 -> 7dbf62d63b1a (head), rename city to address
3b3bc4b2d744 -> 1ee2a1d447d3, change city column type
58c4fd1c59b4 -> 3b3bc4b2d744, add city column to user
ce973c8f81fd -> 58c4fd1c59b4, insert initial users
<base> -> ce973c8f81fd, create people table
```

---

### 5. Сгенерировать SQL-файл (а не просто вывод)

```bash
alembic upgrade ce973c8f81fd:58c4fd1c59b4 --sql > insert_users.sql
```

---

### 6. Важно понимать ограничения

#### ❗ SQL будет:

* **диалект-зависимым**
* **без выполнения**
* **без проверки данных**

#### ❗ Alembic НЕ:

* проверяет существование таблиц
* выполняет `SELECT`
* подставляет реальные значения из Python (кроме констант)

