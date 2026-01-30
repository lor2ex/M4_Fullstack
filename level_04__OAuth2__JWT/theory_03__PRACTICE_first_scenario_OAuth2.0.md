## Пример реализации сценария 1 FastAPI + JWT

Здесь один сервер выполняет роль и авторизационного, и ресурсного.

Мы реализуем:

1. `/token` — выдаёт JWT после проверки логина/пароля (Authorization Server).
2. `/users/me` — защищённый эндпойнт (Resource Server).
3. JWT проверяется на каждом запросе к защищённому эндпойнту.

---

### Установка зависимостей

```bash
pip install fastapi uvicorn python-jose[cryptography] passlib python-multipart
```

* `fastapi` — веб-фреймворк
* `uvicorn` — сервер ASGI
* `python-jose[cryptography]` — для работы с JWT 
  * (более продвинутый вариант по сравнению с `pyjwt`)
* `passlib` — для хэширования паролей
* `python-multipart` — для парсинга форм (`OAuth2PasswordRequestForm`) 

---

### Пример кода

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

# ========================
# Конфигурация
# ========================
SECRET_KEY = "supersecretkey"  # менять на что-то безопасное в проде
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# ========================
# Настройка хэширования паролей
# ========================
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ========================
# "База данных" пользователей (учебный пример)
# ========================
fake_users_db = {
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderland",
        "hashed_password": pwd_context.hash("secret"),  # хэш создаётся при старте
        "disabled": False,
    }
}

# ========================
# Вспомогательные функции
# ========================
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    return db.get(username)

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ========================
# Dependency
# ========================
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username)
    if user is None:
        raise credentials_exception
    return user

# ========================
# Эндпойнты
# ========================
app = FastAPI()

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

```

---

### Проверка работы

1. Запускаем сервер:

```bash
uvicorn main:app --reload
```

2. Получаем токен:

```bash
curl -X POST "http://127.0.0.1:8000/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
-d "grant_type=password&username=alice&password=secret"
```

Ответ примерно:

```json
{
  "access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NDUzOTczOX0.GaLP2oZ8P8CaNau90lkvLJG1fOBEqI8KIAGdHFVeYeA",
  "token_type":"bearer"
}
```

3. Запрашиваем защищённый эндпоинт:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NDUzOTczOX0.GaLP2oZ8P8CaNau90lkvLJG1fOBEqI8KIAGdHFVeYeA" \
http://127.0.0.1:8000/users/me
```

Ответ:

```json
{
  "username":"alice",
  "full_name":"Alice Wonderland",
  "hashed_password":"$pbkdf2-sha256$29000$5JyzNqZ0DgFAqBWCcI4xZg$5oGdMxthUeLCI9P9qa93z6YVhyrA.OOIrJddi3SliV0",
  "disabled":false
}
```

