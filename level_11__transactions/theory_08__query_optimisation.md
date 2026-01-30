## 1. Краткое воспоминание: N+1 запросы в Django

Вспомним, что такое **N+1 проблема**:

```python
# Django
books = Book.objects.all()
for book in books:
    print(book.author.name)  # тут будет отдельный запрос на каждого автора!
```

* **Что происходит:**
  1 запрос на все книги (`SELECT * FROM book`) + N запросов на авторов (`SELECT * FROM author WHERE id=?`)
  → всего N+1 запрос

* **Решение в Django:**
  Используем `select_related` для `ForeignKey` и `prefetch_related` для `ManyToMany`:

```python
books = Book.objects.select_related('author').all()
```

Теперь все данные подтягиваются **за один JOIN**, N+1 нет.

---

## 2. SQLAlchemy: основы загрузки данных и N+1

В SQLAlchemy есть **две концепции загрузки**:

1. **Lazy loading** (по умолчанию) – аналог Django без `select_related`:

   ```python
   books = await session.execute(select(Book)).scalars().all()
   for book in books:
       print(book.author.name)  # отдельный запрос на каждого автора
   ```

2. **Eager loading** – аналог `select_related`/`prefetch_related`:

   * `joinedload()` – делает JOIN и подгружает сразу (аналог `select_related`)
   * `subqueryload()` – делает подзапрос (аналог `prefetch_related`)


### 2.1. Lazy loading (по умолчанию)

**Lazy loading** — это поведение по умолчанию в SQLAlchemy. Аналог Django без `select_related`.
То есть связанный объект **не подгружается сразу**, а SQLAlchemy делает отдельный запрос при первом обращении.

Пример:

```python
    books = await session.execute(select(Book)).scalars().all() # 1 запрос на книги
   for book in books:
       print(book.author.name)  # отдельный запрос на каждого автора 
```

**Что происходит "под капотом":**

1. SQLAlchemy делает запрос:

```sql
SELECT * FROM book;
```

2. Когда вы обращаетесь к `book.author`, SQLAlchemy автоматически делает **новый запрос на автора**:

```sql
SELECT * FROM author WHERE author.id = ?;
```

* Если `books` — это 100 книг, мы получаем **1 + 100 запросов** → типичный N+1.

**Вывод:** lazy loading хорош для одиночных обращений, но для списков объектов — ловушка N+1.

---

### 2.2. Eager loading

Чтобы избежать N+1, SQLAlchemy позволяет **жадно загружать** связанные объекты.
Есть два основных способа:

#### a) `joinedload` — JOIN сразу

* Работает для **ForeignKey / one-to-one** связей
* SQLAlchemy делает **один большой JOIN** и возвращает все данные сразу
* Аналог Django: `select_related`

Пример:

```python
from sqlalchemy.orm import joinedload

books = (await session.execute(
    select(Book).options(joinedload(Book.author))
)).scalars().all()

for book in books:
    print(book.author.name)  # новых запросов нет!
```

SQL-запрос будет примерно такой:

```sql
SELECT book.id, book.title, author.id, author.name
FROM book
JOIN author ON book.author_id = author.id;
```

**Особенности:**

* Очень быстро для маленьких и средних таблиц
* Может быть тяжелым, если связи большие или много JOIN’ов

---

#### b) `subqueryload` — подзапрос

* Работает для **one-to-many / many-to-many** связей
* SQLAlchemy делает **два запроса**:

  1. Основной объект
  2. Подзапрос для связанных объектов
* Аналог Django: `prefetch_related`

Пример:

```python
from sqlalchemy.orm import subqueryload

# Подгружаем книги с жанрами, избегая N+1
books = (await session.execute(
    select(Book).options(subqueryload(Book.genres))
)).scalars().all()

for book in books:
    # Выводим список жанров для каждой книги
    print(book.title, [genre.name for genre in book.genres])
```

SQL-запросы будут примерно такими:

```sql
-- 1. Получаем все книги
SELECT * FROM books;

-- 2. Получаем все жанры для этих книг через подзапрос
SELECT genres.*
FROM genres
JOIN book_genres ON genres.id = book_genres.genre_id
WHERE book_genres.book_id IN (?, ?, ?, ...);
```

**Особенности:**

* Избегает дублирования строк при множественных связях (проблема JOIN)
* Обычно быстрее JOIN для больших many-to-many связей

---
Конечно! Вот аналогичный блок для **`selectinload`** в том же формате:

---

#### c) `selectinload` — отдельный SELECT с `WHERE IN`

* Работает для **one-to-many / many-to-many** связей
* SQLAlchemy делает **два запроса**:

  1. Основной объект
  2. SELECT для связанных объектов с `WHERE IN`
* Аналог Django: `prefetch_related`

Пример:

```python
from sqlalchemy.orm import selectinload

# Подгружаем книги с жанрами, избегая N+1
books = (await session.execute(
    select(Book).options(selectinload(Book.genres))
)).scalars().all()

for book in books:
    # Выводим список жанров для каждой книги
    print(book.title, [genre.name for genre in book.genres])
```

SQL-запросы будут примерно такими:

```sql
-- 1. Получаем все книги
SELECT * FROM books;

-- 2. Получаем все жанры для этих книг через WHERE IN
SELECT genres.*
FROM genres
JOIN book_genres ON genres.id = book_genres.genre_id
WHERE book_genres.book_id IN (?, ?, ?, ...);
```

**Особенности:**

* Избегает дублирования строк при множественных связях (как `subqueryload`)
* Часто **быстрее `subqueryload`**, особенно при большом количестве связанных объектов
* SQL проще и читабельнее, чем при подзапросе (`subqueryload`)

---

## 3. Резюмируем вышесказанное (сравниваем Django и SQLAlchemy)

### 1. Вариант **One-to-Many / ForeignKey**

*(каждая книга имеет один жанр)*

#### Django

```python
books = Book.objects.select_related('genre')
```

* ORM автоматически делает **JOIN** на таблицу жанров
* Результат: **один SQL-запрос** → все книги + жанры
* N+1 **не возникает**

#### SQLAlchemy

```python
from sqlalchemy.orm import joinedload

books = (await session.execute(
    select(Book).options(joinedload(Book.genre))
)).scalars().all()
```

* `joinedload` делает **JOIN**, подтягивая жанр сразу
* Абсолютно аналогично Django `select_related`
* Результат: **один SQL-запрос** → все книги + жанры
* N+1 **не возникает**

**Вывод:** SQLAlchemy полностью повторяет поведение Django для One-to-Many / ForeignKey связей.

---

### 2. Вариант **Many-to-Many**

*(книга ↔ жанры)*

#### Django

```python
books = Book.objects.prefetch_related('genres')
```

* ORM **сама знает промежуточную таблицу** (`book_genres`)
* Делается **подзапрос**, подтягивающий все жанры для выбранных книг одной пачкой
* N+1 **не возникает**

#### SQLAlchemy (вариант 1: `subqueryload`)

```python
from sqlalchemy.orm import subqueryload

books = (await session.execute(
    select(Book).options(subqueryload(Book.genres))
)).scalars().all()
```

* SQLAlchemy делает **два запроса**:

  1. Все книги
  2. Все жанры для этих книг через связующую таблицу `book_genres`

* N+1 **не возникает**, но **нужно явно указать связь через `secondary`**

#### SQLAlchemy (вариант 2: `selectinload`, часто быстрее)

```python
from sqlalchemy.orm import selectinload

books = (await session.execute(
    select(Book).options(selectinload(Book.genres))
)).scalars().all()
```

* Работает почти так же, как `subqueryload`
* Делает второй запрос через `WHERE IN (...)`
* Обычно **быстрее `subqueryload`** при большом числе связанных объектов

**Вывод:** Для Many-to-Many SQLAlchemy ведёт себя аналогично Django `prefetch_related`, но требует явной конфигурации связи и выбора стратегии (`subqueryload` или `selectinload`).

---


### Django ORM vs SQLAlchemy ORM

| Поведение             | Django                                                              | SQLAlchemy                                                                   |
| --------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| One-to-Many / FK      | `select_related`                                                    | `joinedload`                                                                 |
| Many-to-Many          | `prefetch_related`                                                  | `subqueryload` / `selectinload` + `secondary=…`                              |
| Промежуточная таблица | скрыта                                                              | указана явно                                                                 |
| N+1                   | отсутствует при использовании `select_related` / `prefetch_related` | отсутствует при использовании `joinedload` / `subqueryload` / `selectinload` |

