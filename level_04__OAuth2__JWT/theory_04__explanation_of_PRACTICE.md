## Детальное пояснение предыдущего примера

### 1. Настройка

```python
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

* **SECRET_KEY** — ключ, которым мы подписываем JWT.
* **ALGORITHM** — алгоритм подписи JWT (HS256 — HMAC + SHA256).
* **ACCESS_TOKEN_EXPIRE_MINUTES** — время жизни токена.

> В реальном проекте **SECRET_KEY** должен быть случайным и храниться в переменных окружения.

---

### 2. Пользователи

```python
fake_users_db = {
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderland",
        "hashed_password": pwd_context.hash("secret"),  # хэш создаётся при старте
        "disabled": False,
    }
}
```

* Это **имитация базы данных пользователей**.
* Пароль хранится **в хэшированном виде** (`pbkdf2_sha256`), 
  * чтобы не хранить его в открытом виде.
  * в учебном примере мы его создаём прямо в коде из пароля "secret"

> В реальной системе это будет база данных (PostgreSQL, MongoDB и т.д.).

---

### 3. Хэширование и проверка пароля

```python
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
```

* Используем **passlib** для проверки пароля: `verify_password(plain, hashed)`
* Пароль пользователя сравнивается с хэшем.

---

### 4. OAuth2PasswordBearer

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
```

* FastAPI **автоматически разбирает Bearer-токен** из заголовка `Authorization`.
* `tokenUrl="token"` — URL, куда клиент отправляет логин/пароль, чтобы получить токен.

---

### 5. Генерация JWT

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    ...
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

* Формируем payload токена (`sub=username`, `exp=expiration`)
* Подписываем JWT **секретным ключом**
* Возвращаем **короткоживущий токен**, который будет использоваться для авторизации.

---

### 6. Авторизационный сервер

```python
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    ...
    access_token = create_access_token(...)
    return {"access_token": access_token, "token_type": "bearer"}
```

* Клиент (например, фронтенд или Postman) отправляет логин/пароль на `/token`.
* Проверяем пользователя через `authenticate_user`.
* По сути, эта часть не что иное, как аутентификация
* Однако, после этого мы выдаём токен для авторизации (главная задача)
* Поэтому сам сервер называется "авторизационным"
* Генерируем **JWT** и возвращаем его клиенту.

> Это и есть **роль авторизационного сервера**: выдавать токены после проверки учётных данных.

---

### 7. Ресурсный сервер

```python
@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
```

* Любой защищённый эндпоинт требует `current_user`, который **извлекается из токена JWT**.
* Функция `get_current_user` проверяет токен, декодирует его и ищет пользователя в базе.

> Это и есть **ресурсный сервер**: он отдаёт данные, но только авторизованному пользователю.

---

### 8. Клиент

* Любое приложение, которое **делает запросы к API**: фронтенд, мобильное приложение, curl, Postman.
* Оно получает токен `/token`, а потом передаёт его в `Authorization: Bearer <JWT>` при обращении к защищённым ресурсам.

---

### Итоговая логика

1. Клиент отправляет логин/пароль на `/token`.
2. Сервер проверяет пользователя и возвращает JWT.
3. Клиент использует JWT для запросов к защищённым эндпоинтам.
4. Сервер проверяет JWT и отдаёт данные только авторизованным клиентам.

> Таким образом, **один и тот же сервер выполняет роли и авторизационного, и ресурсного сервера**, а JWT — это формат токена, через который реализуется OAuth2.0 Password Flow.


