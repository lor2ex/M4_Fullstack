# 2. Примеры использования индексов в SQLAlchemy 2.0+

## 2.0 Необходимые импорты и класс Base

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Integer, DateTime,
    ForeignKey, Index, UniqueConstraint
)
from datetime import datetime


class Base(DeclarativeBase):
    pass
```

---

## 2.1 Обычный индекс (B-Tree)

### Когда использовать

* частый `WHERE`
* `JOIN`
* `ORDER BY`

### Как

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index("ix_users_email", email),
    )
```

---

## 2.2 UNIQUE индекс

### Когда

* email
* username
* внешний бизнес-ключ

### Как

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )
```

> UNIQUE = уникальность + индекс

---

## 2.3 Составной (composite) индекс

### Когда

* фильтрация по нескольким полям
* `WHERE + ORDER BY`
* `JOIN + фильтр`

### Как

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index(
            "ix_orders_user_created",
            user_id,
            created_at
        ),
    )
```

---

## 2.4 Индекс для FOREIGN KEY (обязательно)

### Когда

* почти всегда при FK
* любые `JOIN`

### Как

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    __table_args__ = (
        Index("ix_orders_user_id", user_id),
    )
```

---

## 2.5 Partial index (PostgreSQL)

### Когда

* soft delete
* статусные записи
* boolean-флаги

### Как

```python
from sqlalchemy import Boolean

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        Index(
            "ix_active_users",
            id,
            postgresql_where=is_active.is_(True)
        ),
    )
```

---

## 2.6 Functional index

### Когда

* `LOWER()`
* `DATE(created_at)`
* `jsonb ->> key`

### Как

```python
from sqlalchemy import func

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index(
            "ix_users_lower_email",
            func.lower(email)
        ),
    )
```

---

## 2.7 Индекс под `ORDER BY`

### Когда

* пагинация
* последние записи

### Как

```python
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index(
            "ix_orders_created_desc",
            created_at.desc()
        ),
    )
```

---

## 2.8 Комбинация: UNIQUE + composite

### Когда

* бизнес-ограничения
* дедупликация

### Как

```python
class UserPhone(Base):
    __tablename__ = "user_phones"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    phone: Mapped[str] = mapped_column(String(32))

    __table_args__ = (
        UniqueConstraint(
            "user_id", "phone",
            name="uq_user_phone"
        ),
    )
```

---

## Краткое правило выбора

| Сценарий          | Индекс                |
| ----------------- | --------------------- |
| `WHERE col = ...` | обычный               |
| `JOIN`            | FK + индекс           |
| `WHERE a AND b`   | composite             |
| `ORDER BY`        | индекс с направлением |
| soft delete       | partial               |
| функции           | functional            |


