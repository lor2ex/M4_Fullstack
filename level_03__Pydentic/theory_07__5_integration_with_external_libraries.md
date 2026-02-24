## Интеграция со сторонними библиотеками

FastAPI + Pydantic позволяют удобно работать с типами и структурами данных,  
которые приходят из сторонних библиотек или сервисов:  
`email`, `URL`, `UUID`, `datetime`, `Decimal`, `JWT`, `OAuth` и т.д.

---

### 1. Валидация URL, Email, UUID

Pydantic предоставляет встроенные типы:

```python
from pydantic import BaseModel, EmailStr, HttpUrl
from uuid import UUID

class UserInfo(BaseModel):
    email: EmailStr
    website: HttpUrl
    user_id: UUID

@app.post("/user-info/")
async def create_user_info(user: UserInfo):
    return user
```

* Любая неправильная структура email, URL или UUID → 422.
* Swagger UI автоматически показывает правильные форматы.

---

### 2. Работа с datetime и Decimal

```python
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

class Transaction(BaseModel):
    amount: Decimal
    timestamp: datetime

@app.post("/transactions/")
async def create_transaction(tx: Transaction):
    return tx
```

* Decimal → точные денежные расчёты.
* datetime → ISO-формат для запросов и ответов.

---

### 3. Pydantic + OAuth / JWT

Можно использовать модели для валидации payload токенов:

```python
from pydantic import BaseModel

class TokenData(BaseModel):
    user_id: int
    scopes: list[str]

def decode_token(token: str) -> TokenData:
    # эмуляция декодирования JWT
    payload = {"user_id": 1, "scopes": ["read", "write"]}
    return TokenData(**payload)

@app.get("/protected/")
async def protected_route(token_data: TokenData = Depends(lambda: decode_token("dummy"))):
    return {"user_id": token_data.user_id, "scopes": token_data.scopes}
```

* Позволяет валидировать токены и payload без ручного парсинга.
* Ошибки структуры токена → 422.

---

### 4. Сложные вложенные JSON-структуры

```python
from typing import List

class Item(BaseModel):
    name: str
    price: float

class Order(BaseModel):
    items: List[Item]
    buyer_email: EmailStr

@app.post("/orders/")
async def create_order(order: Order):
    return order
```

* Позволяет принимать JSON массивы объектов и автоматически валидировать каждое поле.
* Полезно для интеграции с внешними сервисами, где приходят сложные структуры данных.

---

## Итог по теме интеграции со сторонними библиотеками:

* Pydantic предоставляет встроенные типы для **email, URL, UUID, datetime, Decimal**.
* Удобно использовать для **OAuth/JWT**.
* Позволяет валидировать сложные вложенные JSON структуры.
* Все ошибки → корректный HTTP-ответ (422) с информацией об ошибке.

