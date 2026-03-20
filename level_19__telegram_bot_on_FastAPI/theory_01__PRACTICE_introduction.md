## Создание телеграм-бота

### Установка пакета `python-telegram-bot`

```bash
pip install python-telegram-bot

pip freeze > requirements.txt
```


### `simple_bot`

```python
from local_settings import TG_TOKEN


from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters


# Обработчик команды /start
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я твой первый Telegram-бот!")

    
# Обработчик текстовых сообщений
async def echo(update: Update, context):
    user_message = update.message.text
    await update.message.reply_text(f"Вы сказали: {user_message}")


def main():
    # Инициализация приложения
    application = Application.builder().token(TG_TOKEN).build()

    # Подключаем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск бота
    application.run_polling()

    
if __name__ == "__main__":
    main()
```

###  Как работает этот скрипт?

#### 1. Импорт библиотек

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
```

### `from telegram import Update`

Класс `Update` — это **объект любого события в Telegram**.

Когда пользователь что-то делает, Telegram отправляет боту **Update**.
Внутри него может быть:

* сообщение
* команда
* нажатие кнопки
* реакция
* изменение чата

Например, команда `update.message.text` выделяет из сообщения текст пользователя.

---

### `from telegram.ext import ...`

Импортируются основные инструменты бота:

| Класс            | Что делает                   |
| ---------------- | ---------------------------- |
| `Application`    | основной объект бота         |
| `CommandHandler` | обработчик команд (`/start`) |
| `MessageHandler` | обработчик обычных сообщений |
| `filters`        | фильтры для сообщений        |

---

#### 2. Обработчик команды `/start`

```python
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я твой первый Telegram-бот!")
```

**Параметры функции**

* `update` - объект события Telegram 
  * Содержит параметры сообщения и чата
* `context` - объект с дополнительными данными:
  * данные пользователя
  * данные чата
  * доступ к боту
  * аргументы команды

**Метод `.reply_text(text)`**

* Отправляет сообщение `text` в тот же чат.

---

#### 3. Обработчик обычных сообщений

```python
async def echo(update: Update, context):
```

Это функция, которая будет вызываться **для обычных сообщений**.

---

**Извлечение из сообщения текста пользователя**

```python
user_message = update.message.text
```

Например пользователь написал:


**Ответ чата пользователю**

```python
await update.message.reply_text(f"Вы сказали: {user_message}")
```

Чат берёт текст сообщения пользователя `user_message` и добавляет к нему собственный текст (`Вы сказали: `)


---

#### 4. Главная управляющая функция `main()`

Здесь происходит **запуск и настройка бота**.

##### 4.1. Создание объекта приложения с помощью метода `.build()`

```python
application = Application.builder().token(TG_TOKEN).build()
```

Создаётся основной объект бота `Application`. Это **ядро бота**, которое:

* принимает события
* отправляет ответы
* управляет обработчиками

---

##### 4.2. Метод 

Запускает **Builder Pattern** — удобный способ настройки.



##### 4.3. Метод подключение обработчиков `add_handler`

1. **`CommandHandler`**
```python
application.add_handler(CommandHandler("start", start))
```

Подключает `CommandHandler`, которые обрабатывает **команды Telegram**:

* `/start`
* `/help`
* `/settings`

Например, если пользователь пишет: `/start` - запускается функция `start(update, context)`


2. **MessageHandler**
```python
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
```

Обработка текста сообщений.

##### 4.4. Разберём фильтр.

1. `filters.TEXT` 

разрешает **только текстовые сообщения**.

2. `filters.COMMAND`

Сообщения вида:

```
/start
/help
```

3. `~filters.COMMAND`

Инверсия:

```
НЕ команда
```

4. `&`

Логическое **И**

```
TEXT И НЕ COMMAND
```

---

5. Итог

Фильтр пропускает любые текстовые сообщения кроме команд


##### 4.4. async запуск бота

```python
application.run_polling()
```

Метод **polling** запускает сервер на постоянный опрос Telegram:

```
Бот → Telegram: есть сообщения?
Telegram → Бот: да, вот update
Бот → вызывает обработчик
```

Это называется **Long Polling**.

---

### 5. Как работает весь код целиком

Алгоритм:

```
1. Запускается main()
2. Создаётся Application
3. Регистрируются обработчики
4. Бот начинает polling
5. Telegram присылает события
6. Application выбирает нужный handler
7. Вызывается функция (start или echo)
8. Бот отправляет ответ
```
