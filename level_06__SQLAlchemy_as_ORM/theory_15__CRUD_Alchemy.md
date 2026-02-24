## 1. Настройка async сессии

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db", echo=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

```

Все операции выполняются **внутри async сессии**:

```python
async with AsyncSessionLocal() as session:
    # здесь идут все CRUD операции
```

---

## 2. CREATE (вставка)

```python
from models import User  # ORM модель

async with AsyncSessionLocal() as session:
    new_user = User(name="Alice", age=25)
    session.add(new_user)                # добавляем объект
    await session.commit()               # сохраняем в БД
    await session.refresh(new_user)      # обновляем объект из БД (получаем id)
```

**Массовая вставка:**

```python
users = [User(name="Bob"), User(name="Charlie")]
async with AsyncSessionLocal() as session:
    session.add_all(users)
    await session.commit()
```
где `users` — список модели `User`,  например:  
`users = [User(name="Bob"), User(name="Charlie"), ...]`

---

## 3. READ (запросы + агрегаты)

### a) Простые выборки

```python
from sqlalchemy import select

async with AsyncSessionLocal() as session:
    result = await session.execute(select(User).where(User.age >= 18))
    users = result.scalars().all()  # получаем список объектов
```

* `result.scalars()` → только ORM объекты
* `result.scalars().first()` → первая запись или None
* `result.scalar_one()` → одна запись, выбросит исключение, если не одна

[Подробнее здесь](./theory_16__simple_read_queries_SQLAlchemy.md)

---

### b) Агрегатные функции

```python
from sqlalchemy import func

async with AsyncSessionLocal() as session:
    # Кол-во пользователей
    result = await session.execute(select(func.count(User.id)))
    total_users = result.scalar()

    # Средний возраст
    result = await session.execute(select(func.avg(User.age)))
    avg_age = result.scalar()

    # Сумма, максимум, минимум
    result = await session.execute(select(func.sum(User.age), func.max(User.age), func.min(User.age)))
    total, oldest, youngest = result.one()
```

---

### c) Группировка

```python
from sqlalchemy import func

async with AsyncSessionLocal() as session:
    result = await session.execute(
        select(User.age, func.count(User.id))
        .group_by(User.age)
        .having(func.count(User.id) > 1)
    )
    age_groups = result.all()  # [(age, count), ...]
```

---

### d) Оконные функции (window functions)

```python
from sqlalchemy import func, over

async with AsyncSessionLocal() as session:
    stmt = select(
        User.name,
        User.age,
        func.rank().over(order_by=User.age.desc()).label("age_rank")
    )
    result = await session.execute(stmt)
    ranked_users = result.all()  # [(name, age, age_rank), ...]
```

* `func.row_number().over(order_by=...)` — нумерация строк
* `func.rank().over(order_by=...)` — ранг с учётом одинаковых значений

---

## 4. UPDATE

```python
from sqlalchemy import update

async with AsyncSessionLocal() as session:
    stmt = (
        update(User)
        .where(User.name == "Alice")
        .values(age=26)
        .execution_options(synchronize_session="False")  # синхронизация ORM объектов
    )
    await session.execute(stmt)
    await session.commit()
```

* `synchronize_session="fetch"` → обновляет объекты в сессии
* `"evaluate"` → пытается посчитать локально без запроса

---

## 5. DELETE

```python
from sqlalchemy import delete

async with AsyncSessionLocal() as session:
    stmt = delete(User).where(User.age < 18)
    await session.execute(stmt)
    await session.commit()
```

---

## 6. JOIN и сложные запросы

```python
from models import Post
from sqlalchemy import select

async with AsyncSessionLocal() as session:
    stmt = (
        select(User.name, Post.title)
        .join(Post, Post.user_id == User.id)
        .where(User.age >= 18)
    )
    result = await session.execute(stmt)
    data = result.all()  # [(name, title), ...]
```
