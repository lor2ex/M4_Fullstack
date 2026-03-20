## Что такое bs4

`bs4` — это библиотека Python для **построения дерева разбора HTML/XML** и удобной навигации по нему.

[https://beautiful-soup-4.readthedocs.io/en/latest/](https://beautiful-soup-4.readthedocs.io/en/latest/)

Она:

* принимает строку с HTML
* использует выбранный парсер
* строит объектную модель документа
* предоставляет API для поиска и модификации узлов

Важно:
bs4 **не парсер**, а обёртка над парсерами.

**Парсер** — это программа, которая превращает текст по определённым правилам в структурированное дерево данных.

---

### 1.  Установка

```bash
pip install beautifulsoup4 httpx
```

Дополнительно (рекомендуется):

```bash
pip install lxml
```

Если не указать парсер, будет использоваться встроенный `html.parser`.

---

### 2.  Архитектура

Основные типы объектов:

* `BeautifulSoup` — корневой объект
* `Tag` — HTML-тег
* `NavigableString` — текст
* `Comment` — комментарий

Пример:

```python
from bs4 import BeautifulSoup

html = "<div><p>Hello</p></div>"
soup = BeautifulSoup(html, "html.parser")

type(soup)           # BeautifulSoup
type(soup.div)       # Tag
type(soup.p.string)  # NavigableString
```

---

### 3.  Создание объекта

```python
soup = BeautifulSoup(markup, parser)
```

Где `parser`:

* `"html.parser"` — встроенный
* `"lxml"` — быстрый
* `"html5lib"` — максимально корректный

bs4 абстрагирует различия между ними.

---

### 4.  Поиск элементов

#### 4.1 find()

Возвращает первый совпавший элемент.

```python
soup.find("div")
soup.find("div", class_="item")
```

---

#### 4.2 find_all()

Возвращает список (`ResultSet`).

```python
soup.find_all("a")
soup.find_all("div", {"data-id": "123"})
```

---

#### 4.3 select()

Поддержка CSS-селекторов.

```python
soup.select("div.item")
soup.select("#main")
soup.select("ul > li")
```

`select()` возвращает список.

---

### 5.  Атрибуты

Получение:

```python
tag["href"]
tag.get("href")
```

Лучше использовать `.get()` — не выбросит KeyError.

Изменение:

```python
tag["class"] = "new"
```

---

### 6.  Текст

```python
tag.text
tag.get_text(strip=True)
```

`.get_text()` — более гибкий метод.

---

### 7.  Навигация по дереву

#### Родитель

```python
tag.parent
```

#### Дети

```python
tag.children      # генератор
tag.contents      # список
```

#### Соседи

```python
tag.next_sibling
tag.previous_sibling
```

#### Обход всего дерева

```python
tag.descendants
```

---

### 8.  Модификация документа

Изменение имени тега:

```python
tag.name = "span"
```

Удаление:

```python
tag.decompose()
```

Вставка:

```python
new_tag = soup.new_tag("a", href="#")
tag.append(new_tag)
```

---

## Когда использовать

Подходит, если:

* нужно быстро написать парсер
* важна читаемость кода
* объёмы данных умеренные

Не подходит, если:

* нужно обрабатывать гигабайты HTML
* важна максимальная скорость
* нужны сложные XPath-запросы

---
