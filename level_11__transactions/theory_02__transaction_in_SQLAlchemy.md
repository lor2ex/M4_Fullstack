## 1. Создание таблицы и настройка подключения

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    balance = Column(Integer, nullable=False)

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
```

* `asyncpg` — драйвер PostgreSQL, полностью совместимый с пакетом `asyncio` (в простонародии "асинхронный")
* `expire_on_commit=False` — объекты не «умирают» после коммита

---

## 2. Простая async транзакция с явными `commit()` и `rollback()`

```python
import asyncio
from sqlalchemy.exc import SQLAlchemyError

async def withdraw_explicit_commit(account_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        try:
            # Явное начало транзакции (необязательно, session сама её создаёт при DML)
            acc = await session.get(Account, account_id)
            if acc.balance < amount:
                raise ValueError("Недостаточно средств")
            
            acc.balance -= amount
            
            # Явно фиксируем изменения
            await session.commit()
            print(f"Списание {amount} прошло успешно, новый баланс {acc.balance}")
        
        except (ValueError, SQLAlchemyError) as e:
            # Откат транзакции в случае ошибки
            await session.rollback()
            print(f"Откат операции: {e}")

asyncio.run(withdraw_explicit_commit(1, 80))
```
* `await session.commit()`
  * Фиксирует изменения, делает их видимыми для других транзакций.
* `await session.rollback()`
  * Отменяет все изменения, сделанные в текущей транзакции.
* ❗ **Проблема гонки** не решена.
  * `commit()/rollback()` не защищает от гонок, а лишь управляет фиксацией транзакции.

---

## 3. Простая async транзакция с `session.begin()`

```python
import asyncio

async def withdraw(account_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():  # автоматический COMMIT/ROLLBACK
            acc = await session.get(Account, account_id)
            if acc.balance < amount:
                raise ValueError("Недостаточно средств")
            acc.balance -= amount

asyncio.run(withdraw(1, 80))
```

* `session.begin()` — блокирует начало транзакции
* COMMIT при успешном выходе из блока
* ROLLBACK при исключении

❗ **Проблема гонки** остаётся, если два пользователя одновременно делают `SELECT`.

---

## 4. `SELECT … FOR UPDATE` (row-level блокировка)

```python
from sqlalchemy import select

async def withdraw_locked(account_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Account)
                .where(Account.id == account_id)
                .with_for_update()
            )
            acc = result.scalar_one()
            if acc.balance < amount:
                raise ValueError("Недостаточно средств")
            acc.balance -= amount

asyncio.run(withdraw_locked(1, 80))
```

* `.with_for_update()` → ставит **row-level блокировку**
* Пока одна транзакция не сделает COMMIT/ROLLBACK, другая ждёт
* Гонки исключены

---

## 5. Атомарный UPDATE без SELECT

**Эффекта гонок** можно избежать без блокировки:

```python
from sqlalchemy import update

async def withdraw_atomic(account_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(Account)
                .where(Account.id == account_id)
                .where(Account.balance >= amount)
                .values(balance=Account.balance - amount)
                .returning(Account.balance)
            )
            new_balance = result.scalar_one_or_none()
            if new_balance is None:
                raise ValueError("Недостаточно средств")

asyncio.run(withdraw_atomic(1, 80))
```

* `UPDATE ... WHERE balance >= X` — атомарная операция
* Нет риска гонки
* Не нужен `FOR UPDATE`

---

## 6. Резюме

| Метод                                               | Блокировка     | Риск гонки | Применение                                                             |
|-----------------------------------------------------|----------------|------------|------------------------------------------------------------------------|
| Явный `session.commit()/rollback()`                 | ❗ отсутствует  | высокая    | полный (ручной) контроль транзакции, **не для денег**                  |
| `session.begin()` + `session.get()`                 | ❗ отсутствует  | высокая    | авто-контроль транзакции, простой код, **не для денег**                |
| `session.begin()` + `SELECT ... FOR UPDATE`         | ✔ row-level    | нет        | авто-контроль транзакции, банковские операции, перевод средств         |
| `session.begin()` + `UPDATE ... WHERE balance >= X` | атомарная      | нет        | авто-контроль транзакции, безопасный и простой способ списания средств |


