## Добавляем Телеграм

У нас осталось ещё 2 блока, связанных с Телеграм

1. Парсинг телеграм-каналов
2. Публикация сообщений (сгенерированных AI) в собственном телеграм-канале

---


### 1. Добавляем параметры в `local_settings.py`

Все параметры подключение давно уже находится в `local_settings.py` и `config.py`.

Дело за малым:
* проверить актуальность этих данных

`local_settings.py`

```python
# --- Telegram ---------------------------------------------------------------
API_ID = 1234567
API_HASH = "0123456789abcdef0123456789abcdef"
SESSION_STRING = ""
CHANNEL_USERNAME = "@your_news_channel"          # или -1001234567890 (ID канала)

...

# --- Telegram-каналы и сайты -------------------------------------------------
TG_SOURCES = [
    {"name": "@techmedia"},
    {"name": "@IT_today_ru"},
]

SITE_SOURCES = [
    {"name": "habr", "url": "https://habr.com/ru/rss/"},
    {"name": "rbc", "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"},
    {"name": "vc", "url": "https://vc.ru/rss"},
    {"name": "tproger", "url": "https://tproger.ru/feed/"},
]

```

Вносим изменения в `config.py`:
* Добавляем сессионную строку
* Укорачиваем ключи телеграм `app/config.py`:

```python
class Settings(BaseModel):
    tg_api_id: int = API_ID
    tg_api_hash: str = API_HASH
    tg_session_str: str = SESSION_STRING
    tg_channel: str = CHANNEL_USERNAME
    ai_api_key: str = AI_API_KEY
    redis_url: str = REDIS_URL
    parsing_interval_minutes: int = PARSING_INTERVAL_MINUTES
    words: list[str] = KEYWORDS
    tg_sources: list[str] = TG_SOURCES
    site_sources: list[dict] = SITE_SOURCES
    log_level: str = "INFO"
    max_news_per_source_per_run: int = MAX_NEWS_PER_SOURCE_PER_RUN

settings = Settings.model_validate({})   # просто для валидации типов
```

---


### 2. Создаём канал (если ещё не создали)

Подробнее здесь:
[level_20__Telethon_and_Telegram_API/theory_12__PRACTICE_publishing_post_on_the_tg_channel.md](../level_20__Telethon_and_Telegram_API/theory_12__PRACTICE_publishing_post_on_the_tg_channel.md)

---

### 3. Добавляем недостающие пакеты

```bash
pip install telethon

pip freeze > requirements.txt
```

---

### 4. Создаём сессионную строку

💥 Внимание! Изменения!

️⚠️ Чтобы не мучиться с путями к сессионным файлам, создадим сессионную строку.

Подробнее здесь:
[level_20__Telethon_and_Telegram_API/theory_03__PRACTICE_Telegram_session_file.md](../level_20__Telethon_and_Telegram_API/theory_03__PRACTICE_Telegram_session_file.md)

Временно добавляем в проект скрипт для создания сессионного файла:

##### 4.1. Одно-факторная авторизация

`tg_bot.py`

```python
from telethon import TelegramClient
from telethon.sessions import StringSession

from local_settings import API_ID, API_HASH, SESSION_STRING

with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
    print("\n===== Сохраните эту строку в SESSION_STRING =====")
    print( client.session.save())
    print("=================================================\n")
```

##### 4.2. Двух-факторная авторизация

`tg_bot.py`

```python
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from local_settings import API_ID, API_HASH, SESSION_STRING

# Оставь пустым при первом запуске
SESSION_STRING = ""

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def main():
    await client.connect()

    if not await client.is_user_authorized():
        phone = input("Введите телефон: ")
        await client.send_code_request(phone)

        code = input("Введите код: ")

        try:
            await client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            password = input("Введите 2FA password: ")
            await client.sign_in(password=password)

    print("\n===== Сохраните эту строку в SESSION_STRING =====")
    print( client.session.save())
    print("===================================================\n")

with client:
    client.loop.run_until_complete(main())
```
При первом запуске:

1. Telegram попросит **номер телефона** (и ещё пароль, если авторизация дву-факторная)
2. отправит **код в Telegram**
3. вы введёте код

После этого создаётся и выводится в терминал сессионная строка:

```

Please enter your phone (or bot token): +79163500731
Please enter the code you received: 82046
Signed in successfully as Ilya Barbylev; remember to not break the ToS or you will risk an account ban!

===== Сохраните эту строку в SESSION_STRING =====
1BJWap1wBu3X-E8h-YG-YaIgllRYYxq8yxm6A7p0BNltoazYCtqgNEAIiGsEQXrZBDHWtkdyd617v52zGkkpW6pJrZwhRFBwNI_pkjO0v1rO-CwAso=
=================================================
```

Эту строку необходимо сохранить в `local_settings.py` в `SESSION_STRING`.

---

### 5. Добавляем tg_parser

`app/news_parser/telegram.py`

```python
from telethon import TelegramClient
from telethon.sessions import StringSession
from app.config import settings
from app.utils.logging import get_logger
from pathlib import Path

logger = get_logger(__name__)


def pars_tg_channel(channel: str) :
    with TelegramClient(StringSession(settings.tg_session_str), settings.tg_api_id, settings.tg_api_hash) as client:

        posts = []
        for msg in client.iter_messages(channel, limit=settings.max_news_per_source_per_run):
            posts.append({
                "title": '| ',
                "link": f"https://t.me/{channel}/{msg.id}",
                "summary": msg.text,
                "published_at": msg.date
            })

    return posts

if __name__ == '__main__':
    CHANNEL = "@techmedia"

    posts = pars_tg_channel(CHANNEL)
    for post in posts:
        print("title:", post.get('title'))
        print("link:", post.get('link'))
        print("summary:", post.get('summary'))
        print("published_at:", post.get('published_at'))
        print("-" * 40)

```

И сразу же проверяем работу этого телеграм-парсера.


### 6. Добавляем модуль публикации постов на канал

`app/telegram/publisher.py`

```python
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# --- Функция публикации поста ---
def post_to_channel(title: str, text: str):
    with TelegramClient(StringSession(settings.tg_session_str), settings.tg_api_id, settings.tg_api_hash) as client:

        # Получаем сущность канала
        entity = client.get_entity(settings.tg_channel)

        # Формируем сообщение с текущим временем
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"{title}\n\n{text}\n\n🕒 {now}"

        # Отправляем сообщение в канал
        client.send_message(entity, message)
        print(f"Пост отправлен в канал {settings.tg_channel}")



if __name__ == "__main__":
    title = "Тестовый заголовок"
    text = "Это текст поста."
    post_to_channel(title, text)

```

И сразу же проверяем его работоспособность.