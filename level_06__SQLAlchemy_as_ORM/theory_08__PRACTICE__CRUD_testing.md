## Тестируем CRUD database с помощью запросов FastAPI


Всё, что чересчур подробно описано ниже, и так понятно в [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 1. GET `/people/` — получить всех людей

```python
@router.get("/", response_model=List[PersonRead])
async def read_people():
    return await PersonRepository.list_people()
```

#### 🔹 Описание

* **Метод:** `GET`
* **URL:** `/people/`
* **Действие:** возвращает **список всех людей** из таблицы `people`.

#### 🔹 JSON вводить не нужно

* Это `GET` — данные не отправляются.
* В `Swagger UI` нажимаете **Try it out → Execute**.

#### 🔹 Пример ответа сервера

```json
[
  {
    "id": 1,
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com"
  },
  {
    "id": 2,
    "name": "Bob",
    "age": 25,
    "email": "bob@example.com"
  }
]
```

* Список всех записей, каждая с `id`, `name`, `age`, `email`.

---

### 2. POST `/people/` — создать нового человека

```python
@router.post("/", response_model=PersonRead)
async def add_person(person: PersonCreate):
    return await PersonRepository.create_person(person.name, person.age, person.email)
```

#### 🔹 Описание

* **Метод:** `POST`
* **URL:** `/people/`
* **Действие:** добавляет нового человека в таблицу.

#### 🔹 JSON, который вводим через Swagger UI

```json
{
  "name": "Mikal",
  "age": 32,
  "email": "mikal@example.com"
}
```

* Поля соответствуют Pydantic-схеме `PersonCreate`:

  * `name` — строка, обязательна
  * `age` — число, необязательно, но у вас, похоже, nullable=False
  * `email` — строка, уникальна

#### 🔹 Пример ответа сервера

```json
{
  "id": 3,
  "name": "Charlie",
  "age": 35,
  "email": "charlie@example.com"
}
```

* `id` присваивается автоматически в базе.

---

### 3. PUT `/people/{person_id}/email` — обновить email

```python
@router.put("/{person_id}/email")
async def update_email(person_id: int, new_email: str):
    updated = await PersonRepository.update_email(person_id, new_email)
    if not updated:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Email updated successfully"}
```

#### 🔹 Описание

* **Метод:** `PUT`
* **URL:** `/people/{person_id}/email`
* **Действие:** обновляет email конкретного человека по `id`.

### 🔹 JSON вводить через Swagger UI

* FastAPI воспринимает `new_email` как **query parameter**, а не тело.
* То есть в `Swagger UI` появится поле **new_email**, которое нужно заполнить.

Пример запроса:

```
PUT /people/2/email?new_email=bob_new@example.com
```

#### 🔹 Пример ответа сервера

```json
{
  "message": "Email updated successfully"
}
```

* Если `person_id` не найден:

```json
{
  "detail": "Person not found"
}
```

---

### 4. DELETE `/people/{person_id}` — удалить человека

```python
@router.delete("/{person_id}")
async def delete_person(person_id: int):
    deleted = await PersonRepository.delete_person(person_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person deleted successfully"}
```

#### 🔹 Описание

* **Метод:** `DELETE`
* **URL:** `/people/{person_id}`
* **Действие:** удаляет человека по `id`.

#### 🔹 JSON вводить не нужно

* `DELETE` использует только путь (`path parameter`) `person_id`.
* Пример запроса через Swagger UI:

```
DELETE /people/3
```

#### 🔹 Пример ответа сервера

```json
{
  "message": "Person deleted successfully"
}
```

* Если `person_id` не найден:

```json
{
  "detail": "Person not found"
}
```

---

### Итого

| Метод  | URL                | Ввод через JSON / query                                     | Описание                | Пример ответа                               |
| ------ | ------------------ | ----------------------------------------------------------- | ----------------------- | ------------------------------------------- |
| GET    | /people/           | —                                                           | Получить всех людей     | `[{"id":1,"name":"Alice",...},...]`         |
| POST   | /people/           | `{"name":"Charlie","age":35,"email":"charlie@example.com"}` | Создать нового человека | `{"id":3,"name":"Charlie",...}`             |
| PUT    | /people/{id}/email | query param: `new_email`                                    | Обновить email по id    | `{"message":"Email updated successfully"}`  |
| DELETE | /people/{id}       | —                                                           | Удалить человека по id  | `{"message":"Person deleted successfully"}` |


