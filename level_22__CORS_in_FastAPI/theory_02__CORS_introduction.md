### 1. Политика одного источника (Same-Origin Policy)

**Same-Origin Policy** — это правило браузера:

> Скрипт на одной странице может читать данные **только из того же источника (origin)**.

**Источник (origin)** состоит из трёх частей:

* **протокол** (http / https)
* **домен / поддомен**
* **порт**

Например:

| URL                                                    | Тот же origin?          |
| ------------------------------------------------------ | ----------------------- |
| `https://example.com/page` → `https://example.com/api` | ✅ да                    |
| `https://example.com` → `http://example.com`           | ❌ нет (другой протокол) |
| `https://example.com` → `https://api.example.com`      | ❌ нет (другой поддомен) |
| `https://example.com` → `https://example.com:8080`     | ❌ нет (другой порт)     |

### Что SOP запрещает

JavaScript на сайте **не может читать**:

* ответы `fetch` / `XMLHttpRequest` с другого сайта
* DOM чужой страницы в `iframe`
* cookies другого сайта

Пример:

```javascript
fetch("https://api.other-site.com/data")
```

Браузер **заблокирует ответ**, если сервер не разрешил доступ.

---

### 2. CORS (Cross-Origin Resource Sharing)

**CORS** — это механизм, который **позволяет серверу разрешить доступ из другого origin**.

Он работает через **HTTP-заголовки**.

Пример ответа сервера:

```
Access-Control-Allow-Origin: https://example.com
```

Это означает:

> Сервер разрешает сайту `https://example.com` читать ответ.

---

