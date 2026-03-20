## Что такое Dependency Injection (внедрение зависимостей)

**Dependency Injection (DI)** — это способ передавать в функцию или класс то, 
что им нужно для работы (зависимости), *не создавая эти зависимости внутри них*.

Проще говоря:

> **DI позволяет функции не думать, *как* получить данные, сервис, подключение к БД и т.д. — FastAPI сделает это за неё.**

---

### Чем удобны DI?

* изолировать логические части приложения;
* упростить тестирование;
* переиспользовать зависимости;
* отделить бизнес-логику от инфраструктуры (БД, кеш, конфиг).

---

## Почему DI отсутствует в Django?

Django создан **до появления современных практик DI** (2005 год).
Структура Django выглядит так:

* views импортируют всё сами,
* объект запроса (request) создаётся и передаётся вручную,
* работа с БД выполняется напрямую в каждом view,
* middleware даёт ограниченное влияние на зависимость,
* «глобальные» объекты доступны через импорты, а не через DI.


## Отличия FastAPI от Django в контексте DI

| Возможность                                     | FastAPI                 | Django                                    |
| ----------------------------------------------- | ----------------------- | ----------------------------------------- |
| Автоматическое внедрение зависимостей           | ✅ Да                    | ❌ Нет                                     |
| Управление ресурсами (open/close DB)            | ✅ Через Depends + yield | ❌ Делается вручную / middleware           |
| Подмена зависимостей в тестах                   | ✅ Просто                | ❌ Сложно, через monkeypatch или моки      |
| Разделение логики и инфраструктуры              | Отличное                | Ограниченное                              |
| Функции остаются чистыми, без побочных эффектов | Да                      | Нет, часто импортируют глобальные объекты |

DI — это одна из причин, почему 
* FastAPI подходит для современных микросервисов,
* а Django — для более традиционных монолитов.


## Примеры-сравнения FastAPI и Django:

### 1. Работа с базой данных

**Django**

```python
# views.py
from django.http import JsonResponse
from .models import User

def users_view(request):
    users = User.objects.all()  # создаём ORM-запрос прямо здесь
    return JsonResponse(list(users.values()), safe=False)
```

**Минус:** функция сама создаёт зависимость (`User.objects`), её сложно заменить в тестах.

**FastAPI**

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

app = FastAPI()

@app.get("/users")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

**Плюс:** функция `read_users` не создаёт `db` сама — FastAPI внедряет зависимость через `Depends`.

---

### 2. Получение текущего пользователя (авторизация)

**Django**

```python
def me_view(request):
    user = request.user  # напрямую используем request
    if not user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    return JsonResponse({"username": user.username})
```

**Минус:** проверка пользователя встроена в view, переиспользовать логику сложно.


**FastAPI**

```python
from fastapi import Depends, FastAPI, HTTPException

def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@app.get("/me")
def read_me(current_user = Depends(get_current_user)):
    return {"username": current_user.username}
```

**Плюс:** `read_me` получает готового пользователя через DI, логику авторизации легко переиспользовать.

---

### 3. Замена зависимостей для тестов

### Django

```python
# Замена ORM или сервисов требует правки view или использования патчей
```

### FastAPI

```python
def fake_get_db():
    class FakeDB:
        def query(self, model):
            return [{"id": 1, "name": "Alice"}]
    yield FakeDB()

def test_users():
    response = client.get("/users", dependencies=[Depends(fake_get_db)])
    assert response.json() == [{"id": 1, "name": "Alice"}]
```

**Плюс:** FastAPI позволяет легко подставлять фиктивные зависимости через DI, не меняя основной код.
