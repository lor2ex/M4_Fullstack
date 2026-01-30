## Простые выборки (Read / SELECT)

```python
from sqlalchemy import select
from models import User

async with AsyncSessionLocal() as session:
    pass
```

### 1. Все записи

```python
    result = await session.execute(select(User))
    users = result.scalars().all()  # список объектов User
```

### 2. Первая запись

```python
    result = await session.execute(select(User))
    user = result.scalars().first()  # первый объект или None
```

### 3. Одна запись с проверкой

```python
    result = await session.execute(select(User).where(User.id == 1))
    user = result.scalar_one()  # выбросит исключение, если 0 или >1
```

### 4. Одна запись или None

```python
    result = await session.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()  # вернёт объект или None
```

### 5. Выбор только определённых колонок

```python
    result = await session.execute(select(User.name, User.age))
    data = result.all()  # [(name, age), ...]
```

### 6. Выбор с сортировкой

```python
    result = await session.execute(select(User).order_by(User.age.desc()))
    users = result.scalars().all()  # список пользователей по убыванию возраста
```

### 7. Лимит и оффсет (pagination)

```python
    result = await session.execute(select(User).order_by(User.id).limit(5).offset(10))
    users = result.scalars().all()  # 5 пользователей, начиная с 11-го
```

### 8. Фильтр с несколькими условиями

```python
from sqlalchemy import and_, or_

    result = await session.execute(
        select(User).where(
            and_(User.age >= 18,  User.active.is_(True))
        )
    )
    users = result.scalars().all()
    
    # или через or_
    result = await session.execute(
        select(User).where(or_(User.name == "Alice", User.name == "Bob"))
    )
    users = result.scalars().all()
    
   # или через in_
    result = await session.execute(
        select(User).where(User.name.in_(["Alice", "Bob"]))
    )
    users = result.scalars().all()    
```

### 9. Проверка на NULL / NOT NULL

```python
result = await session.execute(
    select(User).where(User.last_login.is_not(None))  # NOT NULL
)
# или
result = await session.execute(
    select(User).where(User.last_login.is_(None))  # NULL
)
```

### 10. LIKE / ILIKE

```python
    result = await session.execute(select(User).where(User.name.like("A%")))
    users = result.scalars().all()
    
    result = await session.execute(select(User).where(User.name.ilike("%bob%")))
    users = result.scalars().all()
```

### 11. DISTINCT

```python
    result = await session.execute(select(User.age).distinct())
    ages = [row[0] for row in result.all()]  # уникальные значения возраста
```

### 12. JOIN с выборкой связанных объектов

```python
    from models import Post

    stmt = select(User, Post).join(Post, Post.user_id == User.id)
    result = await session.execute(stmt)
    data = result.all()  # [(User, Post), ...]
```

Следует помнить, что join() может дать дубликаты User. Поэтому стоит добавить `.distinct()`
```python
    from models import Post

    stmt = select(User, Post).join(Post, Post.user_id == User.id).distinct()
    result = await session.execute(stmt)
    data = result.all()  # [(User, Post), ...]
```

### 13. Подзапросы (subquery)

```python
    subq = select(User.id).where(User.age > 30).subquery()
    result = await session.execute(select(User).where(User.id.in_(subq)))
    users = result.scalars().all()
```

---

💡 **Ключевые методы Result:**

| Метод                         | Что возвращает                                               |
| ----------------------------- |--------------------------------------------------------------|
| `result.scalars()`            | Итератор ORM объектов (или отдельных колонок)                            |
| `result.scalars().all()`      | Список всех строк, каждая как tuple (для нескольких колонок) |
| `result.scalars().first()`    | Первый ORM-объект или None                                      |
| `result.scalar_one()`         | Ровно одно значение (один ORM-объект или колонка), иначе исключение      |
| `result.scalar_one_or_none()` | Один ORM-объект или колонка, или None                                         |


