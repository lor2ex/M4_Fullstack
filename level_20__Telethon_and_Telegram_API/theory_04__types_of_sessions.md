### Типы сессий

В библиотеках вроде Telethon (и аналогично в Pyrogram) сессия — это объект,   
который хранит **данные авторизации Telegram**.

В Telethon есть несколько вариантов хранения сессий:

| тип            | описание                |
| -------------- | ----------------------- |
| file session   | обычный `.session` файл |
| string session | сессия в строке         |
| memory session | временная               |


### 1. Файловая сессия (File Session)

Подробно рассмотрена в предыдущем блоке


---

### 2. Строковая сессия (String Session)

**Идея:**
сессия хранится **не в файле**, а **в одной строке**.

Эта строка содержит закодированные данные:

* ключ авторизации
* id пользователя
* дата-центр Telegram
* параметры соединения

---

#### Пример создания

```python
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = 123456
api_hash = "abcdef123456"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())
```

После авторизации программа выведет строку вроде:

```
1ApWapzMBu...
```

Это и есть **string session**.

---

#### Пример использования

```python
from telethon import TelegramClient
from telethon.sessions import StringSession

session = "1ApWapzMBu..."

client = TelegramClient(StringSession(session), api_id, api_hash)
client.start()
```

Теперь **код подтверждения больше не нужен**.

---

#### String session удобна когда:

* нельзя хранить файлы
* код запускается на сервере
* используется **Docker**
* используется **serverless**

Например:

```
ENV TELEGRAM_SESSION=1ApWapzMBu...
```

---

#### Плюсы

✔ нет файлов  
✔ легко переносить между серверами  
✔ удобно хранить в `.env`

---

#### Минус

⚠️ строка даёт **полный доступ к аккаунту**, поэтому её нужно хранить как **секрет**.

---

### 3. Временная сессия (Memory Session)

**Идея:**
сессия хранится **только в памяти процесса**.

После завершения программы **она исчезает**.

---

#### Пример

```python
from telethon import TelegramClient
from telethon.sessions import MemorySession

client = TelegramClient(MemorySession(), api_id, api_hash)

client.start()
```

---

#### Что происходит

Каждый запуск:

1. программа стартует
2. Telegram отправляет **код**
3. пользователь вводит код
4. программа работает
5. программа завершается
6. **сессия удаляется**

---

#### Где это используют

Memory session полезна когда:

* скрипт запускается **один раз**
* безопасность важнее удобства
* нельзя сохранять данные на диск
* тестирование

---

#### Сравнение типов сессий

| тип            | где хранится    | повторный вход |
| -------------- | --------------- | -------------- |
| file session   | `.session` файл | без кода       |
| string session | строка          | без кода       |
| memory session | RAM             | код каждый раз |

