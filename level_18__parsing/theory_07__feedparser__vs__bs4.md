### Чем `feedparser` отличается от `BeautifulSoup`?

`feedparser` — это библиотека для разбора RSS/Atom-лент (то есть **структурированных фидов новостей**),  
а не произвольного HTML (`BeautifulSoup`).

| Задача                                           | feedparser           | BeautifulSoup (bs4)    |
| ------------------------------------------------ | -------------------- | ---------------------- |
| Разобрать RSS/Atom                               | ✅ Да (основная цель) | ⚠️ Можно, но неудобно  |
| Разобрать обычную HTML-страницу                  | ❌ Нет                | ✅ Да                   |
| Работать с DOM-деревом                           | ❌ Нет DOM            | ✅ Есть дерево          |
| CSS-селекторы                                    | ❌ Нет                | ✅ Да                   |
| Получить структуру записи (title, link, summary) | ✅ Да (готовые поля)  | ❌ Нужно искать вручную |

---

### 1. Базовая теория: что парсит feedparser

RSS/Atom — это **XML-документы строго заданной структуры**.

Пример RSS:

```xml
<rss>
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Новость</title>
      <link>https://example.com/1</link>
      <description>Текст</description>
    </item>
  </channel>
</rss>
```

`feedparser`:

* скачивает XML
* разбирает его
* превращает в Python-объект со словарями

---

### 2. Базовое использование

```python
import feedparser

FEED_URL = "https://habr.com/ru/feed/"

feed = feedparser.parse("https://example.com/rss")

print(feed.keys())
```

**Получаем структура объекта `feed`**:

```
dict_keys([
    'bozo', 
    'entries', 
    'feed', 
    'headers', 
    'href', 
    'status', 
    'encoding', 
    'bozo_exception', 
    'version', 
    'namespaces'
])
```

---

#### 1. `entries`

Главное поле.

Это список всех новостей (элементов `<item>` в RSS или `<entry>` в Atom).

```python
feed.entries[0]
```

Аналог в bs4:

```python
soup.find_all("item")
```

---

#### 2. `feed`

Метаданные канала.

Это данные из `<channel>` в RSS:

* название
* описание
* ссылка
* язык
* дата обновления

Пример:

```python
feed.feed.title
feed.feed.link
feed.feed.description
```

Аналог в bs4:
это как найти `<channel>` и читать его теги вручную.

---

#### 3. `bozo`

Флаг ошибки разбора.

```python
if feed.bozo:
    print("Есть ошибка")
```

* `0` → всё нормально
* `1` → XML кривой или есть проблема

---

#### 4. `bozo_exception`

Если `bozo == 1`, тут лежит объект ошибки.

```python
print(feed.bozo_exception)
```

Это очень полезно при отладке.

---

#### 5. `headers`

HTTP-заголовки ответа сервера.

Например:

```python
feed.headers['content-type']
feed.headers['etag']
feed.headers['last-modified']
```

Это уже не про XML, а про HTTP-ответ.

---

#### 6. `href`

URL, который реально был использован.

Если были редиректы — тут финальный адрес.

---

#### 7. `status`

HTTP-статус:

```python
200
301
404
```

Полезно проверять:

```python
if feed.status != 200:
    print("Проблема с загрузкой")
```

---

#### 8. `encoding`

Кодировка документа:

```python
'utf-8'
```

---

#### 9. `version`

Версия фида:

* `'rss20'`
* `'rss10'`
* `'atom10'`

Это важно, если нужно понимать структуру.

---

#### 10. `namespaces`

Если в фиде есть namespace (например `media:`), они будут тут.

Пример:

```python
feed.namespaces
```

Может вернуть:

```python
{'media': 'http://search.yahoo.com/mrss/'}
```

Это нужно для работы с дополнительными тегами.

---

#### 11. Таким, образом

`feedparser.parse()` возвращает **один большой объект-словарь**, который делится на:

```
feed
 ├── метаданные (feed)
 ├── записи (entries)
 └── техническая информация (status, headers, bozo и т.д.)
```

BeautifulSoup даёт `DOM-дерево`, а feedparser возвращает **уже разобранную структуру данных**.
Где вместо поисков тегов и селекторов мы получаем готовые поля.

**В 90% случаев обычно нужно только**:
* `feed.entries`
* `feed.feed.title`

**Остальное — для диагностики и продвинутой работы.**

---

### 3. Как получить отдельные параметры?

**Обычно доступны**:

```python
entry.title
entry.link
entry.summary
entry.published
entry.author
entry.tags
entry.id
```

Посмотреть всё:

```python
for key in entry.keys():
    print(key)
```

---

### 4. Как листать страницы?

В RSS **обычно нет страниц**, посколку RSS — это:

* последние N новостей
* обновляется автоматически

Если сайт поддерживает pagination RSS (редко), он обычно:

* даёт разные URL
* или указывает `next` ссылку в Atom

Для их "перелистывания":

* используют параметр в URL (`https://habr.com/ru/feed/page2/`)
* или парсят сайт через `requests + bs4`

---

