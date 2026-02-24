## Чем установка FastAPI отличается от установки Django?

Django — это полноценный фреймворк со встроенным WSGI-сервером.  
Его достаточно просто установить и запустить.

FastAPI — минималистичный awaitable фреймворк, который дополнительно  
требует установки такого же awaitable ASGI-сервера (например, `uvicorn`).

```bash
pip install fastapi uvicorn
```


### Примерная структура FastAPI-проекта

Главное отличие от Django в том, что эта структура не создаётся автоматически.  
Её создаёт сам разработчик.

```
my_fastapi_project/
├── requirements.txt       # Список зависимостей
├── app/                   # Основной пакет приложения
│   ├── __init__.py
│   ├── main.py            # Точка входа приложения
│   │
│   ├── core/              # Настройки и конфиги
│   │   └── config.py
│   ├── models/            # ORM-модели или Pydantic-модели
│   │   └── user.py
│   ├── schemas/           # Pydantic-схемы для запросов и ответов
│   │   └── user_schema.py
│   ├── routers/           # Роутеры (эндпоинты)
│   │   └── users.py
│   ├── services/          # Бизнес-логика (необязательно)
│   │   └── user_service.py
│   └── templates/         # Шаблоны для рендеринго
│       └── index.html
└── tests/                 # Тесты
    └── test_users.py

```

Для этой структуры запускается командой

```bash
uvicorn app.main:app --reload
```
где  
`main`      — имя файла без `.py`  
`app`       — объект приложения  
`--reload`  — авто-перезапуск при изменениях  

### Простейший вариант

**Структура проекта**

```
my_fastapi_app/
   └── main.py           
```

Для этой структуры запускается командой

```bash
uvicorn main:app --reload
```

**`FastAPI/main.py`**

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello world"}
```   

### Пример рендеринга HTML-шаблона

FastAPI — это в первую очередь API-фреймворк.  
Но рендерить страницы он тоже может.

Для начала придётся установить недостающий пакет:

```bash
pip install jinja2
```

(Как видим, базовый FastAPI облегчён до предела!)


**Структура проекта**

```
my_fastapi_app/
    └── app/  
        ├── __init__.py
        ├─ main.py
        │
        └─ templates/
           └─ books.html
```

**`FastAPI/main.py`**


```python
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Для простоты список берётся из словаря, а не из БД
books = [
    {"title": "Мастер и Маргарита", "author": "Михаил Булгаков"},
    {"title": "1984", "author": "Джордж Оруэлл"},
    {"title": "Три товарища", "author": "Эрих Мария Ремарк"},
]

@app.get("/books", response_class=HTMLResponse)
async def show_books(request: Request):
    return templates.TemplateResponse(
        "books.html",
        {
            "request": request,
            "books": books,
        }
    )
```    

**`FastAPI/app/templates/books.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Любимые книги</title>
</head>
<body>
    <h1>Список книг</h1>

    <ul>
        {% for book in books %}
        <li>
            <strong>{{ book.title }}</strong> — {{ book.author }}
        </li>
        {% endfor %}
    </ul>
</body>
</html>
```

## ⚠️ `async def` vs `def`

В наших предыдущих примерах нет никаких await-операций,  
поэтому наши эндпойнты можно запускать в двух вариантах: 
и как корутины, и как обычные функции.

Тем не менее корутины предпочтительнее. Почему?

* FastAPI запускается на awaitable ASGI-сервере.
  * (поэтому при прочих равных, корутины сработают чуть-чуть быстрее
  * потому что не требуют переключения в отдельный поток.)
* Когда в эндпойнты появятся await-операции - ничего не придётся переписывать.
