Попробуем разобрать RSS-ленту сайта `https://habr.com/ru/feed/`.

(RSS-версия: `https://habr.com/ru/rss/`).

```python
import feedparser

FEED_URL = "https://habr.com/ru/rss/"

feed = feedparser.parse(FEED_URL)

posts = []
for entry in feed.entries:
    posts.append({
        "title": entry.title,
        "link": entry.link,
        "published": entry.published,
        "summary": entry.summary,
        "author": entry.author,
        "tags": entry.tags,
        "id": entry.id,
        "html_article:": entry.content[0].value,
    })

for post in posts[:2]:
    print(f"\n{25 * "="} post id: {post.get("id")} {25 *"="}")
    print("title:", post.get("title"))
    print("link:", post.get("link"))
    print("published:", post.get("published"))
    print("summary:", post.get("summary"))
    print("author:", post.get("author"))
    print("tags:", post.get("tags"))
    print("article:" )

```

Получим примерно такой результат:

```
========================= post id: https://habr.com/ru/articles/1002812/ =========================
title: Шифрование метаданных в мессенджере: HMAC-SHA256 анонимные пары, timing obfuscation и отравление собственных логов
link: https://habr.com/ru/articles/1002812/?utm_source=habrahabr&utm_medium=rss&utm_campaign=1002812
published: Mon, 23 Feb 2026 20:29:13 GMT
summary: <img src="https://habrastorage.org/getpro/habr/upload_files/1c9/d2c/a6f/1c9d2ca6f9302106608ef2a606f021b0.png" /><p>&gt; <em>«Мы знаем, что вы вчера в 23:47 переписывались с Алексеем 14 минут. О содержании разговора нам неизвестно.»</em>  </p><p>&gt; — Так выглядит мир, где сообщения зашифрованы, а метаданные — нет.</p><p>Привет, Хабр! Я занимаюсь разработкой open-source мессенджера (проект Xipher, C++/Android), и один из компонентов, который пришлось проектировать с нуля — <strong>защита метаданных</strong>. Не содержимого сообщений (E2EE сейчас есть у всех), а информации о самом факте общения: кто с кем, когда, сколько раз.</p><p>В этой статье я подробно разберу инженерные решения, к которым пришёл, — от криптографических примитивов до С++ кода и SQL-схемы. Все примеры — из реального работающего кода. В конце честно расскажу, где подход имеет ограничения и чем отличается от того, что делают Signal и Tor.</p><p><em>Исходники проекта открыты — ссылка на GitHub в конце статьи, если захотите покопаться или раскритиковать.</em></p> <a href="https://habr.com/ru/articles/1002812/?utm_source=habrahabr&amp;utm_medium=rss&amp;utm_campaign=1002812#habracut">Читать далее</a>
author: Svortex
tags: [{'term': 'metadata encryption', 'scheme': None, 'label': None}, {'term': 'HMAC-SHA256', 'scheme': None, 'label': None}, {'term': 'E2EE', 'scheme': None, 'label': None}, {'term': 'traffic analysis', 'scheme': None, 'label': None}, {'term': 'anonymous messaging', 'scheme': None, 'label': None}, {'term': 'C++', 'scheme': None, 'label': None}, {'term': 'информационная безопасность', 'scheme': None, 'label': None}, {'term': 'криптография', 'scheme': None, 'label': None}, {'term': 'метаданные', 'scheme': None, 'label': None}, {'term': 'open source', 'scheme': None, 'label': None}]

========================= post id: https://habr.com/ru/articles/1002810/ =========================
title: Хроники цифровых заводов. Уровни и ошибки
link: https://habr.com/ru/articles/1002810/?utm_source=habrahabr&utm_medium=rss&utm_campaign=1002810
published: Mon, 23 Feb 2026 20:18:18 GMT
summary: <img src="https://habrastorage.org/getpro/habr/upload_files/796/026/de5/796026de5b7757534debfccf6f0ce124.jpg" /><p>Когда речь заходит про умные заводы, «темные производства», цифровых двойников, промышленный интернет вещей и вообще будущее многие настолько воодушевляются, что упускают из фокуса важные вещи. А именно – общую логику построения систем автоматизации заводов.</p><p>Основы основ, описанные в ISA-95 или ГОСТ Р МЭК 62264-1-2014, всегда звучат в рассказах, презентациях или описаниях. Авторы используют такие термины, как SCADA, PLC, IIoT-платформа или MES. Но вот правила работы и уровни промышленной автоматизации часто трактуют неверно.&nbsp;</p><p>И это очень зря. Уровни автоматизации – это такая особенная штука, которая при неудачном смешивании может вызвать целую кучу проблем. Потому всегда нужно держать в голове пирамидку АСУ ТП/АСУП, о которой мы сегодня и поговорим. И не пугайтесь. Как и всегда, я постараюсь рассказать понятно даже о самом сложном. Добро пожаловать в основы Цифрового Завода.</p> <a href="https://habr.com/ru/articles/1002810/?utm_source=habrahabr&amp;utm_medium=rss&amp;utm_campaign=1002810#habracut">Для продолжения процесса нажмите кнопку</a>
author: Interfer
tags: [{'term': 'PLC', 'scheme': None, 'label': None}, {'term': 'MES', 'scheme': None, 'label': None}, {'term': 'scada', 'scheme': None, 'label': None}, {'term': 'erp', 'scheme': None, 'label': None}, {'term': 'bi', 'scheme': None, 'label': None}, {'term': 'ISA-95', 'scheme': None, 'label': None}, {'term': 'плк', 'scheme': None, 'label': None}, {'term': 'асу тп', 'scheme': None, 'label': None}, {'term': 'iiot', 'scheme': None, 'label': None}, {'term': 'сезон heavy digital', 'scheme': None, 'label': None}]

```

Как видим, в `summary` содержится html-код статью.  
Чтобы разобрать его — воспользуемся `BeautifulSoup`:


### Пример разбора `summary`

```python
import feedparser
from bs4 import BeautifulSoup

...
posts = []
for entry in feed.entries:
    summary_html = entry.summary
    soup = BeautifulSoup(summary_html, "html.parser")
    
    # удалить картинку (если не нужна)
    for img in soup.find_all("img"):
        img.decompose()
    
    # получить чистый текст
    text = soup.get_text(separator="\n").strip()

```

Таким образом, полный код:

```python
import feedparser
from bs4 import BeautifulSoup

FEED_URL = "https://habr.com/ru/rss/"

feed = feedparser.parse(FEED_URL)

posts = []
for entry in feed.entries:
    summary_html = entry.summary
    soup = BeautifulSoup(summary_html, "html.parser")

    # удалить картинку (если не нужна)
    for img in soup.find_all("img"):
        img.decompose()

    # получить чистый текст
    text = soup.get_text(separator="\n").strip()

    posts.append({
        "text": text,
        "title": entry.title,
        "link": entry.link,
        "published": entry.published,
        "summary": entry.summary,


        "author": entry.author,
        "tags": entry.tags,
        "id": entry.id,
    })

for post in posts[:2]:
    print(f"\n{25 * "="} post id: {post.get("id")} {25 *"="}")
    print("text:", post.get("text"))
    print("title:", post.get("title"))
    print("link:", post.get("link"))
    print("published:", post.get("published"))
    print("summary:", post.get("summary"))
    print("author:", post.get("author"))
    print("tags:", post.get("tags"))


```

И новый результат:

```
========================= post id: https://habr.com/ru/articles/1002824/ =========================
text: TLDR: Создана рабочая легковесная реализация AmneziaWG для Mikrotik для подключения к AmneziaWG серверам.
Генератор на основе AWG-конфига: 
https://amneziawg-mikrotik.github.io/awg-proxy/configurator.html
Github: 
https://github.com/amneziawg-mikrotik/awg-proxy
 
Читать далее
title: Наконец-то: AmneziaWG в Mikrotik
link: https://habr.com/ru/articles/1002824/?utm_source=habrahabr&utm_medium=rss&utm_campaign=1002824
published: Mon, 23 Feb 2026 21:21:01 GMT
summary: <img src="https://habrastorage.org/getpro/habr/upload_files/9da/3d8/f56/9da3d8f56e00e695da16e6aee02b772a.jpg" /><p>TLDR: Создана рабочая легковесная реализация AmneziaWG для Mikrotik для подключения к AmneziaWG серверам.</p><p>Генератор на основе AWG-конфига: <a href="https://amneziawg-mikrotik.github.io/awg-proxy/configurator.html" rel="noopener noreferrer nofollow">https://amneziawg-mikrotik.github.io/awg-proxy/configurator.html</a></p><p>Github: <a href="https://github.com/amneziawg-mikrotik/awg-proxy" rel="noopener noreferrer nofollow">https://github.com/amneziawg-mikrotik/awg-proxy</a></p> <a href="https://habr.com/ru/articles/1002824/?utm_source=habrahabr&amp;utm_medium=rss&amp;utm_campaign=1002824#habracut">Читать далее</a>
author: TimsTims
tags: [{'term': 'amneziawg', 'scheme': None, 'label': None}, {'term': 'wireguard', 'scheme': None, 'label': None}, {'term': 'mikrotik', 'scheme': None, 'label': None}, {'term': 'vpn', 'scheme': None, 'label': None}, {'term': 'amneziavpn', 'scheme': None, 'label': None}, {'term': 'blake2s', 'scheme': None, 'label': None}, {'term': 'noise protocol', 'scheme': None, 'label': None}]

========================= post id: https://habr.com/ru/articles/1002812/ =========================
text: «Мы знаем, что вы вчера в 23:47 переписывались с Алексеем 14 минут. О содержании разговора нам неизвестно.»
 — Так выглядит мир, где сообщения зашифрованы, а метаданные — нет.
Привет, Хабр! Я занимаюсь разработкой open-source мессенджера (проект Xipher, C++/Android), и один из компонентов, который пришлось проектировать с нуля — 
защита метаданных
. Не содержимого сообщений (E2EE сейчас есть у всех), а информации о самом факте общения: кто с кем, когда, сколько раз.
В этой статье я подробно разберу инженерные решения, к которым пришёл, — от криптографических примитивов до С++ кода и SQL-схемы. Все примеры — из реального работающего кода. В конце честно расскажу, где подход имеет ограничения и чем отличается от того, что делают Signal и Tor.
Исходники проекта открыты — ссылка на GitHub в конце статьи, если захотите покопаться или раскритиковать.
 
Читать далее
title: Шифрование метаданных в мессенджере: HMAC-SHA256 анонимные пары, timing obfuscation и отравление собственных логов
link: https://habr.com/ru/articles/1002812/?utm_source=habrahabr&utm_medium=rss&utm_campaign=1002812
published: Mon, 23 Feb 2026 20:29:13 GMT
summary: <img src="https://habrastorage.org/getpro/habr/upload_files/1c9/d2c/a6f/1c9d2ca6f9302106608ef2a606f021b0.png" /><p><em>«Мы знаем, что вы вчера в 23:47 переписывались с Алексеем 14 минут. О содержании разговора нам неизвестно.»</em> — Так выглядит мир, где сообщения зашифрованы, а метаданные — нет.</p><p>Привет, Хабр! Я занимаюсь разработкой open-source мессенджера (проект Xipher, C++/Android), и один из компонентов, который пришлось проектировать с нуля — <strong>защита метаданных</strong>. Не содержимого сообщений (E2EE сейчас есть у всех), а информации о самом факте общения: кто с кем, когда, сколько раз.</p><p>В этой статье я подробно разберу инженерные решения, к которым пришёл, — от криптографических примитивов до С++ кода и SQL-схемы. Все примеры — из реального работающего кода. В конце честно расскажу, где подход имеет ограничения и чем отличается от того, что делают Signal и Tor.</p><p><em>Исходники проекта открыты — ссылка на GitHub в конце статьи, если захотите покопаться или раскритиковать.</em></p> <a href="https://habr.com/ru/articles/1002812/?utm_source=habrahabr&amp;utm_medium=rss&amp;utm_campaign=1002812#habracut">Читать далее</a>
author: Svortex
tags: [{'term': 'metadata encryption', 'scheme': None, 'label': None}, {'term': 'HMAC-SHA256', 'scheme': None, 'label': None}, {'term': 'E2EE', 'scheme': None, 'label': None}, {'term': 'traffic analysis', 'scheme': None, 'label': None}, {'term': 'anonymous messaging', 'scheme': None, 'label': None}, {'term': 'C++', 'scheme': None, 'label': None}, {'term': 'информационная безопасность', 'scheme': None, 'label': None}, {'term': 'криптография', 'scheme': None, 'label': None}, {'term': 'метаданные', 'scheme': None, 'label': None}, {'term': 'open source', 'scheme': None, 'label': None}]

```

---

### Что с помощью `BeautifulSoup` можно извлечь ещё?

#### 1. Первая картинка

```python
img = soup.find("img")
if img:
    print(img["src"])
```

#### 2.  Ссылка «Читать далее»

```python
read_more = soup.find("a")
if read_more:
    print(read_more["href"])
```

#### 3.  Все параграфы

```python
for p in soup.find_all("p"):
    print(p.get_text())
```

---

#### 4. Если нужен только текст без HTML вообще

Самый простой вариант:

```python
clean_text = BeautifulSoup(entry.summary, "html.parser").get_text()
```

---

### RSS-лента `https://www.rbc.ru/`

```python
import feedparser

FEED_URL = "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"

feed = feedparser.parse(FEED_URL)

print("Статус:", feed.status)
print("Количество статей:", len(feed.entries))
print()

for entry in feed.entries[:2]:
    print(f"\n{25 * "="} post id: {entry.id} {25 *"="}")
    print("Заголовок:", entry.title)
    print("Ссылка:", entry.link)
    print("Текст:", entry.summary)
    print("published:", entry.published)

```

### RSS-лента `https://vc.ru/`

```python
import feedparser

FEED_URL = "https://vc.ru/rss"

feed = feedparser.parse(FEED_URL)

print("Статус:", feed.status)
print("Количество статей:", len(feed.entries))
print()

for entry in feed.entries[:2]:
    print(f"\n{25 * "="} post id: {entry.id} {25 *"="}")
    print("Заголовок:", entry.title)
    print("Ссылка:", entry.link)
    print("Текст:", entry.summary)
    print("published:", entry.published)

```

### RSS-лента `https://tproger.ru/`

```python
import feedparser

FEED_URL = "https://tproger.ru/feed/"

feed = feedparser.parse(FEED_URL)

print("Статус:", feed.status)
print("Количество статей:", len(feed.entries))
print()

for entry in feed.entries[:2]:
    print(f"\n{25 * "="} post id: {entry.id} {25 *"="}")
    print("Заголовок:", entry.title)
    print("Ссылка:", entry.link)
    print("Текст:", entry.summary)
    print("published:", entry.published)

```