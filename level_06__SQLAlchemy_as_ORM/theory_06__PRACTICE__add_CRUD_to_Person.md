## Добавляем CRUD-операции для таблицы SQLAlchemy + PostgreSQL (async)

В реальных проектах CRUD-операции обычно выносят в отдельный модуль.  
Например, можно добавить `crud_person.py`.

### 1. Структура проекта после изменения

```
project/
│── docker-compose.yml
│── .env
│── database.py
│── models_person.py
│── load_data.py
│── crud_person.py      <-- новый файл
│── main.py
│── people.json
```

---

### 2. Новый файл `crud_person.py`



```python
from sqlalchemy import select, func
from database import AsyncSessionLocal
from models_person import Person

# ----------- CRUD функции -------------

async def is_table_empty() -> bool:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Person))
        return count == 0

async def get_people():
    async with AsyncSessionLocal() as session:
        result = await session.scalars(select(Person))
        return result.all()

async def create_person(name: str, age: int, email: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            person = Person(name=name, age=age, email=email)
            session.add(person)
        await session.commit()
        return person

async def update_person_email(person_id: int, new_email: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Получаем объект из базы
            person = await session.get(Person, person_id)
            if person:
                person.email = new_email
                # session.commit() не нужен внутри begin(), он выполнится после выхода
        # После выхода из блока begin() изменения автоматически зафиксируются

async def delete_person(person_id: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            person = await session.get(Person, person_id)
            if person:
                await session.delete(person)
        # После выхода из блока begin() удаление будет зафиксировано
```

---

### 3. Обновлённый `main.py`

```python
import asyncio
from load_data import load_people_from_json, init_db
from crud_person import (
    is_table_empty, get_people, create_person, update_person_email, delete_person
)

async def main():
    await init_db()

    if await is_table_empty():
        print("Таблица пуста. Загружаем people.json ...")
        await load_people_from_json("people.json")
    else:
        print("Таблица уже содержит данные.")

    print("\nСодержимое таблицы после загрузки:")
    people = await get_people()
    for p in people:
        print(f"{p.id}: {p.name}, {p.age}, {p.email}")

    # ---- Create ----
    print("\nДобавляем нового человека Dave ...")
    await create_person("Dave", 28, "dave@example.com")

    # ---- Update ----
    print("\nОбновляем email Alice ...")
    await update_person_email(1, "alice_new@example.com")

    # ---- Delete ----
    print("\nУдаляем Bob ...")
    await delete_person(2)

    # ---- Read после изменений ----
    print("\nСодержимое таблицы после изменений:")
    people = await get_people()
    for p in people:
        print(f"{p.id}: {p.name}, {p.age}, {p.email}")

if __name__ == "__main__":
    asyncio.run(main())

```

### 4. Запуск и проверка работы

После выполнения `main.py` должно быть что-то вроде

```
...
2025-12-07 21:39:55,041 INFO sqlalchemy.engine.Engine ROLLBACK
3: Charlie, 35, charlie@example.com
4: Dave, 28, dave@example.com
1: Alice, 30, alice_new@example.com
```

Как видим,
1. Был добавлен `Dave`
2. Изменился email у `Alice`
3. Был удалён  `Bob`