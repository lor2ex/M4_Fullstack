### 1. Как создать Telegram-бота и получить токен

1. Откройте Telegram.
2. В поиске найдите бота **BotFather**.
3. Нажмите **Start**.
4. Отправьте команду:

```
/newbot
```

5. BotFather попросит:

* **Название бота** (любое, например: My Test Bot)
* **Username бота** (должен заканчиваться на `bot`, например `my_test_example_bot`)

6. После этого BotFather отправит сообщение с **API Token**, например:

```
1234567890:AAFZ-Py2OLz5R0KjmVmXAc3_2ozdЕHdSUZzI
```

7. Cохраните его в `local_settings.py` или `env`

---

### 2. Проверим правильность `TG_TOKEN`

`checking_tg_token.py`

```python
import httpx
import json
from pprint import pprint

from local_settings import TG_TOKEN

response = httpx.get(f"https://api.telegram.org/bot{TG_TOKEN}/getMe")

pprint(
    json.loads(response.text)
)

```

**Должно вернуться что-то вроде этого**:

```
{
    'ok': True,
    'result': {
        'allows_users_to_create_topics': False,
        'can_connect_to_business': False,
        'can_join_groups': True,
        'can_read_all_group_messages': False,
        'first_name': 'JavaRushIlya',
        'has_main_web_app': False,
        'has_topics_enabled': False,
        'id': 8677207960,
        'is_bot': True,
        'supports_inline_queries': False,
        'username': 'JavaRushILYAbot'
    }
}
```

---

### 3. Как управлять ботом

Через BotFather можно менять настройки.

Основные команды:

| Команда           | Что делает              |
| ----------------- | ----------------------- |
| `/mybots`         | управление всеми ботами |
| `/setname`        | изменить имя            |
| `/setdescription` | описание                |
| `/setabouttext`   | текст “About”           |
| `/setuserpic`     | аватар                  |
| `/setcommands`    | список команд           |
| `/deletebot`      | удалить бота            |

Самый удобный способ управления:

```
/mybots
```

Дальше выберите нужного бота и откроется меню.

---

### 4. Как удалить токен и создать новый (сброс токена)

Если произошла утечка токена (или просто решили его обновить):

1. Откройте **BotFather**
2. Отправьте команду: `/mybots`
  * появляется кнопки с именами ваших ботов 
3. Выбираете имя нужного бота
4. выбираете `API token`:
  * появится токен 
  * и ниже кнопка его отзыва: `Revoke current token`
5. нажимаете -> и получаете новый токен
  * ❗️ старый токен может ещё действовать в течение нескольких минут

---

### 5. Как полностью удалить бота

1. Откройте BotFather
2. Отправьте команду: `/mybots`
  * появляется кнопки с именами ваших ботов 
3. Выбираете имя нужного бота
4. Выбираете `Delete Bot`
   * После подтверждения:
     * бот будет **полностью удалён**
     * токен станет **недействительным**

---

### 6. Полезные команды BotFather

```
/start
/newbot
/mybots
/setcommands
/setdescription
/setabouttext
/setuserpic
/revoke
/deletebot
```

---

### 7. Советы по безопасности

⚠️ Никогда:

* НЕ публикуйте токен
* НЕ отправляйте его другим людям
* НЕ выкладывайте в GitHub

Если произошла утечка токена, немедленно его обновите! 

