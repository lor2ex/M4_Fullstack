### Хранение сессий пользователя

В FastAPI нет автоматического создания сессионного ключа при первом запросе как в Django.  
Поэтому механизм создания и проверки сессионного ключа необходимо прописывать самостоятельно.

> Справедливости ради надо отметить, что для этой цели существуют готовые пакеты:
> * `fastapi-sessions`
> * `fastsession`
> * и так далее.
> 
> Но и здесь также можно использовать Redis


#### Общая идея архитектуры

* `/login` — создаёт сессию
* Redis — хранит данные пользователя
* Cookie `session_id` — идентификатор сессии
* `get_current_user` — dependency для защиты эндпойнтов
* `/protected` — эндпойнт, доступный только залогиненным


1. При авторизации пользователя на `/login` создаётся сессионный ключ `session_id`,  
который записывается в cookies браузера.  

2. Одновременно с этим, по ключу `session_id` в Redis записываются данные пользователя,  
которые пользователь сообщил при авторизации.

3. С каждый новым запросом браузер отправляют cookies. Поэтому по `session_id` мы безошибочно определяем,
является ли пользователь аутентифицированным или нет.

4. И, зная `session_id`, можем легко извлечь из Redis предварительно сохранённые данные пользователя.


#### Эндпойнт авторизации 

```python
import uuid
from pydantic import BaseModel

# Модель пользователя
class User(BaseModel):
    id: int
    username: str
    password: str
    role: str = "user"


@app.post("/login")
async def login(user: User, response: Response, client: Redis = Depends(get_redis)):
    # В реальности тут проверка логина/пароля
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "password": user.password,
        "role": user.role
    }

    session_id = str(uuid.uuid4())

    await client.set(f"session:{session_id}", json.dumps(user_data), ex=3600)

    # FastAPI автоматически возвращает response вместе с JSON ответом
    response.set_cookie(key="session_id", value=session_id)
    
    return {"status": "logged in"}
```

* Пользователь передаёт JSON со своими данными при запросе.
* В учебном примере мы опускаем проверку пароля
  * валидируем переданные данные с помощью Pydentic
  * и сохраняем их в виде строки в Redis
* Создаём уникальный сессионный ключ `session_id = str(uuid.uuid4())`
* Записываем его в response и передаём в браузер

#### Обработка запроса клиента

```python
async def get_current_user(request: Request, client: Redis = Depends(get_redis)):
    session_id = request.cookies.get("session_id")

    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await client.get(f"session:{session_id}")

    if not data:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return json.loads(data)


@app.get("/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Access granted",
        "user": current_user
    }
```

Для облегчения эндпойнта, логика проверки сессионного ключа и извлечения данных из Redis  
выведена в отдельную функцию `get_current_user`, которая с помощью зависимостей передаётся в эндпойнт.


#### Проверка работы

1. Сразу же попробуем обратиться к защищённому эндпойнту:

[http://127.0.0.1:8000/protected](http://127.0.0.1:8000/protected)

**Ответ**:

```json
{
  "detail":	"Not authenticated"
}
```

2. Аутентифицируемся (через [http://127.0.0.1:8000/docs#/](http://127.0.0.1:8000/docs#/))


3. Теперь снова пробуем обратиться к защищённому эндпойнту:

[http://127.0.0.1:8000/protected](http://127.0.0.1:8000/protected)

**Ответ**:

```json
{
  "message": "Access granted",
  "user": {
    "user_id": 0,
    "username": "string",
    "password": "string",
    "role": "user"
  }
}
```

4. Удалим ключ из Redis

Проще всего перезапустить контейнер с Redis

5. Снова обращаемся к protected:

[http://127.0.0.1:8000/protected](http://127.0.0.1:8000/protected)

**Ответ**:

```json
{
  "detail": "Session expired or invalid"
}
```

6. Удаляем cookies из браузера

Правая кнопка на любое место браузера -> Inspect -> Storage -> Cookies

Далее находим строчку с session_id и удаляем

7. Снова обращаемся к protected:

[http://127.0.0.1:8000/protected](http://127.0.0.1:8000/protected)

**Ответ**:

```json
{
  "detail":	"Not authenticated"
}
```