### 1. `app/db/sql/database.py`

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.db.sql.models import Base

load_dotenv()

DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('SQL_DB_HOST')}:{os.getenv('SQL_DB_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Dependency для маршрутов
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ---- функция для создания всех таблиц ----
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

```

---

### 2. `app/db/sql/models.py`

```python
from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum
import datetime

Base = declarative_base()

class OrderStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    price = Column(DECIMAL(10, 2))
    stock = Column(Integer)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(OrderStatus), default=OrderStatus.pending)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price = Column(DECIMAL(10,2))
    order = relationship("Order", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(DECIMAL(10,2))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    paid_at = Column(DateTime)

```

---

### 3. Пример CRUD для SQL — `app/db/sql/crud.py`

```python
from sqlalchemy.future import select
from .models import User, Product, Order, OrderItem, Payment
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, email: str):
    user = User(username=username, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_product(db: AsyncSession, product_data):
    product = Product(**product_data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_all_products(db: AsyncSession):
    result = await db.execute(select(Product))
    return result.scalars().all()


async def get_product(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


```

---

### 4. `app/db/mongo/database.py`

```python
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}"
client = AsyncIOMotorClient(MONGO_URI)
db = client[os.getenv("MONGO_DB_NAME")]

```

---

### 5. `app/db/mongo/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class Review(BaseModel):
    product_id: int
    user_id: int | None = None
    username: str | None = None
    rating: int = Field(..., ge=1, le=5)
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    id: str | None = None
```

---

### 6. Пример CRUD для MongoDB — `app/db/mongo/crud.py`

```python
from .database import db
from .models import Review

async def create_review(review: Review):
    doc = review.model_dump()
    result = await db.reviews.insert_one(doc)
    return str(result.inserted_id)

async def get_reviews_by_product(product_id: int):
    cursor = db.reviews.find({"product_id": product_id})
    reviews = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        reviews.append(doc)
    return reviews

```
