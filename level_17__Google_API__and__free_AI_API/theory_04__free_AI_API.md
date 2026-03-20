### AI чат бот ApiFreeLLM

Сервис обещает **полностью бесплатный API с неограниченным использованием**  
и без обязательной привязки банковской карты:

* нужно войти через Google,
* подключить Discord (для бесплатного доступа)
* получить персональный API‑ключ
* и использовать его в заголовке Authorization. 

---

### Как получить API‑ключ на ApiFreeLLM

1. Откройте сайт: **[https://apifreellm.com](https://apifreellm.com)** или [https://apifreellm.com/en/api-access](https://apifreellm.com/en/api-access) 
2. Нажмите кнопку **Get Free API Key / Get your free API key**. 
3. Войдите через **Google‑аккаунт** (без карты). 
4. Сразу после входа получите ваш **API‑ключ** (обычно отображается в панели). 

   * Иногда требуется привязать Discord к аккаунту для активации ключа. 
5. Скопируйте этот ключ — он будет выглядеть как длинная строка.

После этого вы можете использовать его в запросах.
---

## Пример Python кода с этим API‑ключом

API‑запросы через этот сервис выполняются к endpoint:

```
POST https://apifreellm.com/api/v1/chat
```

Аутентификация происходит через заголовок **Authorization: Bearer YOUR_API_KEY**. ([ApiFreeLLM][1])

Пример Python-кода:

```python
import requests

API_KEY = "ВАШ_API_KEY_ОТ_ApiFreeLLM"

url = "https://apifreellm.com/api/v1/chat"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

data = {
    "message": "Привет! Напиши короткое приветствие."
}

response = requests.post(url, headers=headers, json=data)

print(response.json())
```

---

## Что ожидать

Бесплатный доступ без карты.  
Ключ не истекает, используется в заголовке Authorization.  
Ограничение по скорости: обычно будет задержка ~5–25 сек между запросами на бесплатном плане. ([ApiFreeLLM][3])

---

