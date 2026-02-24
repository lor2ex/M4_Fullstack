### Изменённый код `main.py`

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel

# ========================
# Конфигурация
# ========================
SECRET_KEY = "supersecretkey"  # менять на что-то безопасное в проде
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

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
        "hashed_password": pwd_context.hash("secret"),
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
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
# Pydantic модели
# ========================
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ========================
# FastAPI приложение
# ========================
app = FastAPI()

# ========================
# Эндпоинт: login (Password Grant)
# ========================
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
    refresh_token = create_refresh_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# ========================
# Эндпоинт: обновление токена
# ========================
@app.post("/token/refresh")
async def refresh_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Неверный refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный refresh token")

    user = get_user(fake_users_db, username)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    access_token = create_access_token(
        data={"sub": username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ========================
# Эндпоинт: защищённый
# ========================
@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

```

### Проверка работы:

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

**Ответ примерно:**

```json
{
  "access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NDYyNzM5MH0.nb1GFdaf7kyK4MJKESEp-aG5BVa4tgIPZKZY6RBYI74",
  "refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NTIzMDM5MH0.QHEAC9gEST_8FPVXUPhzQBVBMGk_cJKayiGrv-3Ul0Q",
  "token_type":"bearer"
}
```

3. Запрос на обновление access token

```bash
curl -X POST "http://127.0.0.1:8000/token/refresh" \
-H "Content-Type: application/json" \
-d '{"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NTIzMDM5MH0.QHEAC9gEST_8FPVXUPhzQBVBMGk_cJKayiGrv-3Ul0Q"}'
```

**Ответ примерно:**

```json
{
  "access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NDYyNzgzNn0.gdr87tIOzpTWABTdbZAh1bs5q-Dz1fNOV8T1hbw80kM",
  "token_type":"bearer"
}
```

4. Запрашиваем защищённый эндпойнт:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc2NDYyNzgzNn0.gdr87tIOzpTWABTdbZAh1bs5q-Dz1fNOV8T1hbw80kM" \
http://127.0.0.1:8000/users/me
```

Ответ:

```json
{
  "username":"alice",
  "full_name":"Alice Wonderland",
  "hashed_password":"$pbkdf2-sha256$29000$LiVEyLnXujcmpBQCwDiHUA$Dz42ne4mHdW5IkeJyJlunEc11xV.88e4DioN0/ZUTLs",
  "disabled":false
}
```

