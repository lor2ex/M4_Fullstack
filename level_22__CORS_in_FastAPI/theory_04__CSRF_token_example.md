### Пример использования CSRF токена в FastAPI

FastAPI, отличии от Django, не имеет готовой структуры генерации CSRF токенов.

Но зато имеет несколько сторонних библиотек, которые могут помочь, например `fastapi-csrf-protect`.

Эта библиотека делает всё что нужно:

* генерирует CSRF-токен
* кладёт его в cookie
* даёт вставить токен в форму
* проверяет при отправке


### Установка

```bash
pip install fastapi-csrf-protect
```

---

### Пример кода

```python
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

app = FastAPI()

# Конфиг
class CsrfSettings(BaseModel):
    secret_key: str = "supersecretkey"

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# Отдаём HTML-форму со встроенным CSRF токеном
@app.get("/form", response_class=HTMLResponse)
def form(request: Request, csrf_protect: CsrfProtect = Depends()):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    html = f"""
    <form action="/submit" method="post">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <input type="text" name="username">
        <button type="submit">Send</button>
    </form>
    """

    response = HTMLResponse(content=html)
    csrf_protect.set_csrf_cookie(signed_token, response)

    return response

# Обрабатываем принятую от клиента форму с CSRF токеном
@app.post("/submit")
def submit(
    request: Request,
    username: str = Form(...),
    csrf_protect: CsrfProtect = Depends()
):
    csrf_protect.validate_csrf(request)

    return {"message": f"Hello, {username}!"}
```

---


#### 1. Генерация токенов

```python
csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
```

* `csrf_token` → вставляется в форму
* `signed_token` → кладётся в cookie

---

#### 2. Вставка в форму

```html
<input type="hidden" name="csrf_token" value="...">
```

---

#### 3. Просим браузер вернуть cookie с CSRF токеном

```python
csrf_protect.set_csrf_cookie(signed_token, response)
```

Браузер автоматически отправит её обратно

---

#### 4. Проверяем, тот ли CSRF токен нам прислали

```python
csrf_protect.validate_csrf(request)
```

Сравниваем **токен из формы** с **токеном из cookie**.
