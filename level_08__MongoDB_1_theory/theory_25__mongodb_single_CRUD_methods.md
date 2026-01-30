В противовес методу `aggregate()`, который может использовать различные стадии,  
предложены "одиночные" методы mongodb-запросов.

| Операция               | Метод PyMongo           | Пример использования                                                        | Описание                                                                               |
| ---------------------- | ----------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Создание**           | `insert_one()`          | `coll.insert_one({"name": "Alice", "age": 25})`                         | Вставляет один документ в коллекцию.                                                   |
|                        | `insert_many()`         | `coll.insert_many([{"name": "Bob"}, {"name": "Carol"}])`                | Вставляет несколько документов сразу.                                                  |
| **Чтение (один)**      | `find_one()`            | `user = coll.find_one({"name": "Alice"})`                               | Возвращает первый документ, соответствующий фильтру.                                   |
| **Чтение (много)**     | `find()`                | `users = coll.find({"age": {"$gt": 20}})`                               | Возвращает все документы, соответствующие фильтру (Cursor).                            |
| **Обновление (один)**  | `update_one()`          | `coll.update_one({"name": "Alice"}, {"$set": {"age": 26}})`             | Обновляет первый найденный документ.                                                   |
| **Обновление (много)** | `update_many()`         | `coll.update_many({"age": {"$lt": 20}}, {"$set": {"status": "minor"}})` | Обновляет все подходящие документы.                                                    |
| **Замена документа**   | `replace_one()`         | `coll.replace_one({"name": "Alice"}, {"name": "Alice", "age": 30})`     | Полностью заменяет документ новым.                                                     |
| **Удаление (один)**    | `delete_one()`          | `coll.delete_one({"name": "Bob"})`                                      | Удаляет первый найденный документ.                                                     |
| **Удаление (много)**   | `delete_many()`         | `coll.delete_many({"age": {"$lt": 18}})`                                | Удаляет все документы, соответствующие фильтру.                                        |
| **Подсчёт**            | `count_documents()`     | `count = coll.count_documents({"age": {"$gte": 18}})`                   | Возвращает количество документов по фильтру.                                           |
| **Сортировка и лимит** | `find().sort().limit()` | `coll.find().sort("age", -1).limit(5)`                                  | Сортировка (`1` — по возрастанию, `-1` — по убыванию) и ограничение числа результатов. |



### Пример использования

```python
from pprint import pprint
from pymongo import MongoClient  # pip install pymongo

MONGODB_URL_ATLAS = 'mongodb+srv://ibarbylev5_db_user:adgsdfg5Rt@cluster0.3clfuwg.mongodb.net/'

with MongoClient(MONGODB_URL_ATLAS) as client:
    db = client["db_name"]
    result = db["collection_name"].find({"name": "Alice"})
    
    for doc in result:
        pprint(doc)
```

