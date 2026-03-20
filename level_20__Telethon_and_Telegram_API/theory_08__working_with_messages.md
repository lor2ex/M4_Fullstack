### Работа с сообщениями

После того как клиент получил **сущность**, можно работать с сообщениями внутри неё.

Сообщения представлены объектом:

```text
Message
```

Большинство операций Telethon связано именно с сообщениями.

Например:

```python
await client.send_message(entity, "Hello")
```

---

#### 1. Отправка сообщений

Самая базовая операция — отправка сообщения.

```python
await client.send_message(entity, "Hello")
```

Пример:

```python
channel = await client.get_entity("python")

await client.send_message(channel, "Hello from Telethon")
```

Можно также указать получателя напрямую:

```python
await client.send_message("python", "Hello")
```

---

#### 2. Получение сообщений

Метод `get_messages()` позволяет получить список сообщений.

```python
messages = await client.get_messages(entity, limit=10)
```

Пример:

```python
for msg in messages:
    print(msg.text)
```

Параметр `limit` указывает количество сообщений.

---

#### 3. Чтение истории сообщений

Если нужно прочитать **большое количество сообщений**, удобнее использовать `iter_messages()`.

Этот метод возвращает **асинхронный итератор**.

```python
async for message in client.iter_messages(entity):
    print(message.text)
```

Так можно пройти по всей истории чата.

---

#### 4. Отправка файлов

Telethon поддерживает отправку файлов.

```python
await client.send_file(entity, "image.png")
```

Можно отправлять:

* изображения
* видео
* документы
* аудио

Пример:

```python
await client.send_file("python", "photo.jpg")
```

---

#### 5. Работа с объектами Message

Каждое сообщение — это объект `Message`.

Например:

```python
for msg in messages:
    print(msg.id)
    print(msg.text)
    print(msg.date)
```

Некоторые полезные поля:

| поле        | описание                |
| ----------- | ----------------------- |
| `id`        | идентификатор сообщения |
| `text`      | текст сообщения         |
| `date`      | время отправки          |
| `sender_id` | отправитель             |

---

### Итог

Типичная работа с сообщениями выглядит так:

```text
Entity
   ↓
Message
```

Пример:

```python
entity = await client.get_entity("python")

messages = await client.get_messages(entity, limit=10)

for msg in messages:
    print(msg.text)
```

