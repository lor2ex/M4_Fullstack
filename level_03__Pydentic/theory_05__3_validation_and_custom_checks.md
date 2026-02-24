## Валидация и кастомные проверки

FastAPI позволяет использовать Pydantic не только для типизации,  
но и для кастомной логики валидации.  
Как на уровне отдельного поля, так и на уровне всей модели.  

---

### 1. Кастомные валидаторы для полей

В Pydantic v2 используется `@model_validator(mode="before"/"after")` (ранее `@validator` в v1).

```python
from pydantic import BaseModel, ValidationError, model_validator

class UserCreate(BaseModel):
    username: str
    password: str

    @model_validator(mode="before")
    def check_username_length(cls, values):
        username = values.get("username")
        if len(username) < 3:
            raise ValueError("username must be at least 3 characters")
        return values

@app.post("/users/")
async def create_user(user: UserCreate):
    return user
```

* `mode="before"` → проверка до приведения типов.
* Можно валидировать поле до сохранения в БД.

---

### 2. Валидация нескольких полей сразу (root_validator)

Иногда нужно проверять взаимосвязь полей.

```python
class PasswordChange(BaseModel):
    old_password: str
    new_password: str

    @model_validator(mode="after")
    def check_password_diff(cls, values):
        if values['old_password'] == values['new_password']:
            raise ValueError("new_password must be different from old_password")
        return values

@app.post("/change-password/")
async def change_password(pw: PasswordChange):
    return {"status": "ok"}
```

* `mode="after"` → значения уже приведены к нужным типам.
* Позволяет проверять **совместимость нескольких полей**.

---

### 3. Проверка уникальности или логики на уровне схемы

Можно комбинировать Pydantic с `Depends`, чтобы проверять правила в БД:

```python
from fastapi import Depends, HTTPException

fake_db_usernames = ["alice", "bob"]

def check_unique_username(username: str):
    if username in fake_db_usernames:
        raise HTTPException(status_code=400, detail="Username already exists")
    return username

class UserCreateUnique(BaseModel):
    username: str
    password: str

@app.post("/users-unique/")
async def create_user_unique(user: UserCreateUnique = Depends(lambda: UserCreateUnique(username="alice", password="123"),)):
    # Здесь можно вызывать check_unique_username(user.username)
    return user
```

* Можно строить кастомную валидацию с проверкой внешних условий (БД, сервисы).

---

### 4. Использование Pydantic вместе с Depends для сложной логики

FastAPI позволяет комбинировать Pydantic **для параметров запроса и тела запроса** через Depends,  
что удобно для авторизации, фильтров, дополнительных проверок:

```python
from fastapi import Depends, HTTPException

class TokenData(BaseModel):
    user_id: int

def validate_token(token: str):
    if token != "secret":
        raise HTTPException(status_code=401, detail="Invalid token")
    return TokenData(user_id=1)

@app.get("/protected/")
async def protected_route(token_data: TokenData = Depends(validate_token)):
    return {"user_id": token_data.user_id}
```

* Модель Pydantic используется для типизации и валидации данных из Depends.
* Позволяет вынести логику проверки токена или прав доступа.

---

## Итог по теме Валидация и кастомные проверки:

* Кастомные валидаторы проверяют отдельные поля или целую модель.
* `root_validator` / `model_validator(mode="after")` → проверка связей между полями.
* Можно интегрировать валидацию с Depends для внешней логики (БД, авторизация, уникальные значения).
* Ошибки валидации автоматически приводят к корректным HTTP-ответам (422).


