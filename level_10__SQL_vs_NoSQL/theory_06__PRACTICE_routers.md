### 1. `app/routers/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql import crud, database
from pydantic import BaseModel

router = APIRouter()

# Pydantic схемы для запросов и ответов
class UserCreate(BaseModel):
    username: str
    email: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}

# Создание пользователя
@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate, db: AsyncSession = Depends(database.get_db)):
    db_user = await crud.create_user(db, user.username, user.email)
    return db_user

# Получение пользователя по ID
@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(database.get_db)):
    db_user = await crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

```

---

### 2. `app/routers/reviews.py`

```python
from fastapi import APIRouter, HTTPException
from app.db.mongo import crud, models
from pydantic import BaseModel
from typing import List

router = APIRouter()

# Схема для создания отзыва
class ReviewCreate(BaseModel):
    product_id: int
    user_id: int | None = None
    username: str | None = None
    rating: int
    comment: str

# Схема для ответа
class ReviewRead(BaseModel):
    id: str
    product_id: int
    user_id: int | None = None
    username: str | None = None
    rating: int
    comment: str
    created_at: str

# Добавление отзыва
@router.post("/", response_model=ReviewRead)
async def create_review(review: ReviewCreate):
    review_obj = models.Review(**review.model_dump())
    review_id = await crud.create_review(review_obj)

    # Формируем объект ответа
    return ReviewRead(
        id=str(review_id),
        product_id=review_obj.product_id,
        user_id=review_obj.user_id,
        username=review_obj.username,
        rating=review_obj.rating,
        comment=review_obj.comment,
        created_at=review_obj.created_at.isoformat()
    )

# Получение всех отзывов для книги
@router.get("/product/{product_id}", response_model=List[ReviewRead])
async def get_reviews(product_id: int):
    reviews = await crud.get_reviews_by_product(product_id)
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found")
    # Переименуем _id → id для ответа
    for r in reviews:
        r["id"] = r.pop("_id")
        r["created_at"] = r["created_at"].isoformat()
    return reviews
```

---

### 3. `app/routers/products.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql import crud, database
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ProductCreate(BaseModel):
    title: str
    author: str
    price: float
    stock: int

class ProductRead(BaseModel):
    id: int
    title: str
    author: str
    price: float
    stock: int

    model_config = {"from_attributes": True}


@router.post("/", response_model=ProductRead)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(database.get_db)):
    return await crud.create_product(db, product)

@router.get("/", response_model=List[ProductRead])
async def get_products(db: AsyncSession = Depends(database.get_db)):
    return await crud.get_all_products(db)

```


---

### 5. `app/routers/orders.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql import crud, database, models
from pydantic import BaseModel
from typing import List

router = APIRouter()

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]

class OrderRead(BaseModel):
    id: int
    user_id: int
    status: str

    model_config = {"from_attributes": True}


# Создание заказа с транзакцией: создаём Order и уменьшаем stock
@router.post("/", response_model=OrderRead)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(database.get_db)):
    async with db.begin():  # транзакция

        # Проверка существования пользователя
        user_result = await db.execute(
            select(models.User).where(models.User.id == order.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {order.user_id} not found")

        # Создание заказа
        db_order = models.Order(user_id=order.user_id)
        db.add(db_order)
        await db.flush()  # чтобы получить id заказа

        # Обработка каждого товара
        for item in order.items:
            product = await crud.get_product(db, item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Not enough stock for product {item.product_id}"
                )

            # Уменьшаем stock
            product.stock -= item.quantity

            # Создаём OrderItem
            db_item = models.OrderItem(
                order_id=db_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=product.price
            )
            db.add(db_item)

    # Обновляем и возвращаем заказ
    await db.refresh(db_order)
    return db_order

```

---


### 7. app/routers/payments.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql import crud, database, models
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class PaymentCreate(BaseModel):
    order_id: int
    amount: float

class PaymentRead(BaseModel):
    id: int
    order_id: int
    amount: float
    status: str

    model_config = {"from_attributes": True}


@router.post("/", response_model=PaymentRead)
async def create_payment(payment: PaymentCreate, db: AsyncSession = Depends(database.get_db)):
    order = await crud.get_order(db, payment.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db_payment = models.Payment(order_id=payment.order_id, amount=payment.amount,
                                status=models.PaymentStatus.completed, paid_at=datetime.utcnow())
    db.add(db_payment)
    order.status = models.OrderStatus.completed
    await db.commit()
    await db.refresh(db_payment)
    return db_payment

```

---


### Что мы в итоге получили?


1. **SQL роуты (User)**:

   * POST `/users/` — создать пользователя
   * GET `/users/{id}` — получить пользователя

2. **Mongo роуты (Review)**:

   * POST `/reviews/` — добавить отзыв на книгу
   * GET `/reviews/product/{product_id}` — получить все отзывы книги


### 1. **SQL роуты (Product)**

* POST `/products/` — создать книгу
* GET `/products/` — получить список всех книг

> Демонстрирует работу с SQL таблицей `Product`, хранение структурированных данных, возможность фильтрации и сортировки (можно добавить).

---

### 2. **SQL роуты (Order)**

* POST `/orders/` — создать заказ с товарами

> Этот маршрут демонстрирует транзакцию: создаём заказ (`Order`) и `OrderItem` в одной операции, одновременно уменьшаем `stock` у товаров.
> Позволяет показать преимущества SQL для целостности данных при сложных операциях.

---

### 3. **SQL роуты (Payment)**

* POST `/payments/` — оплатить заказ

> Демонстрирует простое изменение статуса заказа и создание платежа в SQL, снова с сохранением целостности данных.
> Можно расширить GET `/payments/{id}` для получения информации о платеже.

---

### 4. **Mongo роуты (Review)**

* POST `/reviews/` — добавить отзыв на книгу
* GET `/reviews/product/{product_id}` — получить все отзывы книги

> Показана гибкость MongoDB: неструктурированные данные, возможность добавлять новые поля без миграций.
> Можно легко агрегировать данные для рейтингов книг.

---



