### Сценарий работы с Telethon

Типичный сценарий работы с Telethon включает **несколько этапов**:

```text id="wf01"
1. Подключение к Telegram
2. Получение сущности (entity)
3. Работа с сообщениями
4. Подписка на события
```

Эта схема повторяется во всех программах и ботах.

---

#### 1. Подключение к Telegram

Сначала создаём клиент:

```python id="wf02"
from telethon import TelegramClient

api_id = 123456   # ваш api_id
api_hash = "abcd1234"  # ваш api_hash

client = TelegramClient("session_name", api_id, api_hash)
```

* `"session_name"` — имя файла сессии (сохраняет авторизацию)
* `api_id` и `api_hash` — данные из [my.telegram.org](https://my.telegram.org)

---

#### 2. Получение сущности

Используем `get_entity()` или `get_dialogs()`, чтобы получить нужный чат, канал или пользователя:

```python
entity = await client.get_entity("python")
```

Теперь `entity` можно использовать для работы с сообщениями или файлами.

---

#### 3. Работа с сообщениями

Например, отправка и получение сообщений:

```python
# отправка сообщения
await client.send_message(entity, "Hello from Telethon!")

# получение последних 10 сообщений
messages = await client.get_messages(entity, limit=10)
for msg in messages:
    print(msg.text)
```

Можно использовать `iter_messages()` для чтения истории:

```python
async for message in client.iter_messages(entity):
    print(message.text)
```

Или отправлять файлы:

```python
await client.send_file(entity, "image.png")
```

---

#### 4. Реакция на события

Подписываемся на события, чтобы реагировать на новые сообщения в реальном времени:

```python
from telethon import events

@client.on(events.NewMessage(chats=entity))
async def handler(event):
    print("Новое сообщение:", event.message.text)
```

Можно добавлять и другие обработчики, например `ChatAction` для действий пользователей.

---

#### 5. Запуск программы

Используем асинхронный цикл клиента:

```python
async def main():
    # пример: отправка сообщения
    await client.send_message(entity, "Workflow test")

with client:
    client.loop.run_until_complete(main())
```

---

### Итоговая схема

```text
TelegramClient
      ↓
получение сущности (entity)
      ↓
работа с сообщениями / файлами
      ↓
подписка на события (NewMessage, ChatAction)
      ↓
реакции в реальном времени
```

Это **типичный рабочий сценарий Telethon**, который можно адаптировать под:

* ботов
* мониторинг чатов
* массовую рассылку
* уведомления

