### 1. Зачем нужны пользовательские исключения?

FastAPI уже умеет возвращать стандартные HTTP-ошибки через `HTTPException`.  
Но иногда в приложении нужны **специфические ошибки**, чтобы:

* сделать код более читаемым;
* унифицировать обработку конкретных ситуаций;
* вернуть клиенту информативное сообщение с конкретным HTTP-кодом;
* интегрировать централизованное логирование через middleware.

Пример:  
отдельное исключение для
* ошибок авторизации, 
* превышения лимита попыток входа
* недоступных внешних сервисов.

---

### 2. Создание пользовательского исключения

В Python пользовательское исключение создаётся через наследование от `Exception` или `HTTPException`.

Пример:

```python
from fastapi import FastAPI, HTTPException

class NotEnoughBalanceException(HTTPException):
    def __init__(self, balance: float, required: float):
        detail = f"Insufficient balance: {balance} available, {required} required."
        super().__init__(status_code=400, detail=detail)
```

Здесь:

* создаётся класс `NotEnoughBalanceException`;
* автоматически устанавливается **статус 400 Bad Request**;
* формируется информативное сообщение для клиента.

---

### 3. Использование пользовательского исключения в эндпойнте

```python
app = FastAPI()

user_balances = {"alice": 50, "bob": 10}

@app.post("/buy-item")
async def buy_item(user: str, price: float):

    balance = user_balances.get(user, 0)

    if balance < price:
        raise NotEnoughBalanceException(balance=balance, required=price)

    user_balances[user] -= price
    return {"user": user, "new_balance": user_balances[user]}
```

Пример работы:

```
POST /buy-item?user=bob&price=20
```

Ответ сервера:

```json
{
  "detail": "Insufficient balance: 10 available, 20 required."
}
```

---

### 4. Централизованная обработка пользовательских исключений

Вместо того чтобы каждый маршрут вручную перехватывал исключения,  
можно использовать **декоратор `exception_handler`** для глобальной обработки.

```python
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(NotEnoughBalanceException)
async def not_enough_balance_handler(request: Request, exc: NotEnoughBalanceException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "BalanceError", "message": exc.detail},
    )
```

Теперь, когда исключение выбрасывается, клиент получает **стандартизированный JSON**:

```json
{
  "error": "BalanceError",
  "message": "Insufficient balance: 10 available, 20 required."
}
```

Преимущества:

* единый формат ответов;
* лёгкое логирование и интеграция с фронтендом;
* код маршрутов остаётся чистым и читаемым.

---

### 5. Пример с разными пользовательскими исключениями

Можно создать несколько исключений для разных случаев:

```python
class UnauthorizedActionException(HTTPException):
    def __init__(self, action: str):
        detail = f"User not allowed to perform action: {action}"
        super().__init__(status_code=403, detail=detail)

class ResourceLockedException(HTTPException):
    def __init__(self, resource: str):
        detail = f"Resource '{resource}' is currently locked"
        super().__init__(status_code=423, detail=detail)
```

Использование:

```python
@app.post("/edit-resource")
async def edit_resource(user_role: str, resource: str):

    if user_role != "admin":
        raise UnauthorizedActionException(action="edit resource")

    # допустим, ресурс временно заблокирован
    raise ResourceLockedException(resource=resource)
```

---

### 6. Итоги

* Пользовательские исключения помогают **структурировать ошибки**, делая код и API понятными.
* Их можно **использовать вместе с глобальными обработчиками** для единого формата JSON.
* Они позволяют **точно контролировать HTTP-код и сообщение** для клиента.
* Можно создавать отдельные исключения под **разные бизнес-сценарии**, что упрощает поддержку больших проектов.

