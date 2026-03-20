### 1. Попробуем сначала получить чистый HTML-код

```python
import httpx

URL = "https://en.wikipedia.org/wiki/REST"

response = httpx.get(URL)
print("status_code =", response.status_code)

html = response.text
print(html[:200])
```
**Результат**:

```
status_code = 403
Please set a user-agent and respect our robot policy https://w.wiki/4wJS. See also https://phabricator.wikimedia.org/T400119.
```

### 2. В чём причина этой ошибки?

Многие сайты придерживаются "анти-ботовой" политика.  
Ещё недавно Википедия в их число не входила.

Минимально простое решение на сегодняшний день - использовать заголовки, имитирующие браузер. 

Открываем:

`Inspection -> Network -> Request Headers`

(Пока достаточно скопировать только `User-Agent`)

```python
headers = {
    "Host": "en.wikipedia.org",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    # Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
    # Accept-Language: en-US,en;q=0.9,ru;q=0.8,bg;q=0.7
    # Accept-Encoding: gzip, deflate, br, zstd
    # Connection: keep-alive
}

response = httpx.get(URL, headers=headers)

```

**Результат**:

```
status_code = 200
<!DOCTYPE html>
<html class="client-nojs vector-feature-language-in-header-enabled vector-feature-language-in-main-page-header-disabled vector-feature-page-tools-pinned-disabled vector-feature-toc-pin
```

### 3. Добавляем обработку ошибок и элементы bs4

```python
import httpx
from bs4 import BeautifulSoup

URL = "https://en.wikipedia.org/wiki/REST"

headers = {
    # "Host": "en.wikipedia.org",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0",
    # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    # Accept-Language: en-US,en;q=0.9,ru;q=0.8,bg;q=0.7
    # Accept-Encoding: gzip, deflate, br, zstd
    # Connection: keep-alive
}

try:
    # Задаём таймаут: connect=5s, read=10s
    response = httpx.get(URL, headers=headers, timeout=httpx.Timeout(5.0, read=10.0))
    response.raise_for_status()  # выбросит исключение, если статус != 200

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # Извлечение заголовков
    titles = soup.find_all("h2")
    for title in titles:
        print(title)
    print('============================================')

    # Извлечение текста заголовков
    for title in titles:
        print('title.text:', title.text)
    print('============================================')

    # Извлечение текста первого параграфа
    paragraph = soup.find("p")
    print('paragraph:', paragraph)
    print('paragraph.text:', paragraph.text)
    print('============================================')

    # Извлечение первой ссылки
    tag_a = soup.find("a")
    print('tag_a:', tag_a)
    print('tag_a.text:', tag_a.text)
    print('tag_a.attrs:', tag_a.attrs)
    print('tag_a["href"] =', tag_a.get("href"))
    print('tag_a.get("class") =', tag_a.get("class"))

except httpx.TimeoutException:
    print("Ошибка: запрос превысил время ожидания!")
except httpx.RequestError as e:
    print(f"Ошибка запроса: {e}")
except httpx.HTTPStatusError as e:
    print(f"Ошибка HTTP: {e.response.status_code}")


```
