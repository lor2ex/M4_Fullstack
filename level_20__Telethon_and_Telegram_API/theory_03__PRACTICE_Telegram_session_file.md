Ещё одно важная часть работы с Telegram-клиентами - сессионный файл.

Удобен для тех, кто не хочет проходить авторизацию каждый раз.

---

### Что такое сессия в Telegram?

После первой авторизации Telegram выдаёт **ключ доступа**, который сохраняется в **session-файле**.

Этот файл содержит данные, позволяющие клиенту:

* не вводить код подтверждения снова
* автоматически входить в аккаунт
* сохранять состояние соединения

---

### Как это работает?

#### 1. Первый запуск 

##### 1.1. Одно-факторная авторизация

`tg_bot.py`

```python
from telethon import TelegramClient

from local_settings import API_ID, API_HASH

client = TelegramClient("tg_session", API_ID, API_HASH)
client.start()
```

##### 1.2. Дву-факторная авторизация

`tg_bot.py`

```python
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from local_settings import API_ID, API_HASH

client = TelegramClient("tg_session", API_ID, API_HASH)

async def main():
    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Phone: ")
        await client.send_code_request(phone)

        try:
            code = input("Code: ")
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input("2FA password: ")
            await client.sign_in(password=password)

with client:
    client.loop.run_until_complete(main())
```
При первом запуске:

1. Telegram попросит **номер телефона** (и ещё пароль, если авторизация дву-факторная)
2. отправит **код в Telegram**
3. вы введёте код

После этого создаётся сессионный файл:

```
tg_session.session
```

---

#### 2. Следующие запуски

Когда скрипт запускается снова, библиотека:

1. читает файл `tg_session.session`
2. использует сохранённые ключи
3. **входит без кода**


| этап               | что происходит     |
| ------------------ | ------------------ |
| первая авторизация | ввод номера и кода |
| создаётся файл     | `.session`         |
| следующие запуски  | вход без кода      |


---

### Где хранится файл `tg_session.session`?

По умолчанию файл создаётся в **текущей папке проекта**.

Пример:

```
project/
    tg_bot.py
    tg_session.session
```

---

### Что хранится в session-файле

Упрощённо:

* ключ авторизации
* id пользователя
* данные дата-центра Telegram
* параметры соединения

Это **не пароль**, но файл даёт **доступ к аккаунту**.

Поэтому его **нельзя публиковать**.

---

### Как выйти из сессии?

1. Либо удалить файл `my_session.session`

2. Либо выйти программно: `await client.log_out()`

И в том, и в другом случае снова потребуется авторизация.

