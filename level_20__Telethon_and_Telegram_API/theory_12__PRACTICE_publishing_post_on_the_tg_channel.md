### Как создать собственный канал в Telegram

1. Откройте Telegram на телефоне или ПК.
2. Нажмите **“Новый канал”** (New Channel).
   * Если не видно этого пункта меню, нажмите значок карандаша ✏️ внизу списка чатов. 
     * Появится меню:
       * Новая группа
       * Новый канал
     * Выберите Новый канал.
3. Придумайте имя и описание.
4. Выберите тип канала:
   * нажмите название канала -> появится знак ✏️
   * выберите `Channel Type`:

      * **Публичный** → получаете username, можно использовать в `get_entity("username")`.
      * **Приватный** → тогда ссылка вида `https://t.me/joinchat/...`.
5. Добавьте хотя бы себя как участника.
6. Готово! Теперь можно тестировать скрипт на этом канале.

---

### Async скрипт: публикация поста с текущим временем

`tg_publish_post_async.py`

```python
import asyncio
from datetime import datetime
from telethon import TelegramClient

from local_settings import API_ID, API_HASH

CHANNEL_USERNAME = "my_java_rash_channel"


client = TelegramClient("tg_session", API_ID, API_HASH)

# --- Функция публикации поста ---
async def post_to_channel(channel_username: str, title: str, text: str):
    # Получаем сущность канала
    entity = await client.get_entity(channel_username)
    
    # Формируем сообщение с текущим временем
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{title}\n\n{text}\n\n🕒 {now}"
    
    # Отправляем сообщение в канал
    await client.send_message(entity, message)
    print(f"Пост отправлен в канал {channel_username}")

# --- Главная функция ---
async def main():
    channel_username = CHANNEL_USERNAME
    title = "Тестовый заголовок"
    text = "Это текст поста."
    await post_to_channel(channel_username, title, text)

# --- Запуск клиента ---
with client:
    client.loop.run_until_complete(main())
```


#### Как это работает:

1. Получаем **entity** канала через `get_entity(channel_username)`.
2. Формируем сообщение: объединяем `title` + `text` + текущее время.
3. Отправляем через `send_message(entity, message)`.



### Sync скрипт: публикация поста с текущим временем

В Telethon есть встроенный sync режим.  
Самый простой способ — использовать модуль `telethon.sync`, который автоматически убирает `await` и `async`.

`tg_publish_post.py`


```python
from datetime import datetime
from telethon.sync import TelegramClient

from local_settings import API_ID, API_HASH

CHANNEL_USERNAME = "my_java_rash_channel"

client = TelegramClient("tg_session", API_ID, API_HASH)


# --- Функция публикации поста ---
def post_to_channel(channel_username: str, title: str, text: str):
    # Получаем сущность канала
    entity = client.get_entity(channel_username)

    # Формируем сообщение с текущим временем
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{title}\n\n{text}\n\n🕒 {now}"

    # Отправляем сообщение в канал
    client.send_message(entity, message)
    print(f"Пост отправлен в канал {channel_username}")


# --- Главная функция ---
def main():
    channel_username = CHANNEL_USERNAME
    title = "Тестовый заголовок"
    text = "Это текст поста."
    post_to_channel(channel_username, title, text)


# --- Запуск клиента ---
if __name__ == "__main__":
    with client:
        main()
```