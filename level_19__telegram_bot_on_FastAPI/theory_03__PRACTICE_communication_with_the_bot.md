### Как найти нашего бота?

#### Способ 1 — через поиск в Telegram

1. Откройте Telegram
2. В строке поиска введите:

```
@JavaRushILYAbot
```

3. Откройте чат с ботом.

---

#### Способ 2 — через прямую ссылку

Откройте ссылку:

```
https://t.me/JavaRushILYAbot
```

Она сразу откроет чат с ботом.

---

### Как запустить бота?

1. Запустите скрипт `simple_bot.py`

2. Затем перейдите в Телеграм чат и нажмите **Start**
   или отправьте команду:

```
/start
```

Ваш код обработает её через:

```python
CommandHandler("start", start)
```

И бот ответит:

```
Привет! Я твой первый Telegram-бот!
```

---

### Как проверить echo

Напишите боту любое сообщение:

```
Привет
```

Он ответит:

```
Ты сказал: Привет
```

Это работает благодаря обработчику:

```python
MessageHandler(filters.TEXT & ~filters.COMMAND, echo)
```

---

### ⚠️ Важный момент

❗ Ваш бот отвечает **только пока запущен Python-скрипт** на вашей машине.


### Добавим обработку команд `/help` и `/about`

Добавляем две новых команды:

```python
async def help_command(update: Update, context):
    """Функция для обработки команды /help"""
    await update.message.reply_text("Я могу повторять ваши сообщения или помочь с чем-то другим. Попробуйте!")

    
async def about_command(update: Update, context):
    """Функция для обработки команды /about"""
    await update.message.reply_text("Я бот, созданный для обучения. Моё назначение - служить вам!")
```

И подключаем их к обработчику в `main`

```python
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("about", about_command))
```

⚠️ Не забудьте перезапустить скрипт!


### Добавляем обработку вопросов пользователя

Попробуем усложнить алгоритм ответов бота:
* настроим специальные ответы на ключевые слова `привет` и `как дела`:
  * `привет` -> `Здравствуйте!\n`
  * `как дела` -> `Спасибо, что спрашиваете!\nМои дела идут хорошо)`


```python
async def echo(update: Update, context):
    user_message = update.message.text

    answer = ''
    if 'привет' in  user_message.lower():
        answer += "Здравствуйте!\n"
    if 'как дела' in user_message.lower():
        answer += "Спасибо, что спрашиваете!\nМои дела идут хорошо)"
    if answer:
        await update.message.reply_text(answer)
    else:
        await update.message.reply_text(f"Вы сказали: {user_message}")
```