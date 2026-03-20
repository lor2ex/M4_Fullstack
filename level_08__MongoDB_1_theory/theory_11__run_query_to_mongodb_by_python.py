from pprint import pprint
from pymongo import MongoClient  # pip install pymongo

from local_settings import MONGODB_URL_ATLAS

with MongoClient(MONGODB_URL_ATLAS) as client:
    TIMES = 5  # число документов на печать по умолчанию
    task_statement = []  # список условий задач
    data = []  # список документов по каждому решению задачи

    """ ********************** Блок задач **************************** """

    # === Задача 1 (пример решения) ===
    task_statement.append(
        'Задача 1: В Atlas.sample_training.companies найти компании, где число сотрудников >= 50'
    )

    # ----- в result подставляем решение из mongodb -----
    result = ''

    data.append(result)

    # ===== Задача 2 =====
    task_statement.append(
        """Задача 2: Найти все предложения Гавайских островов в Atlas.sample_airbnb.listingsAndReviews
        вывод в формате: название, остров, цена
        для справки: должно быть 614 объектов
        (варианты поиска: 
        1. поиск по всем островам
        2. геопространственный поиск)
        """
    )

    # ----- в result подставляем решение из mongodb -----
    result = client['sample_airbnb']['listingsAndReviews'].aggregate([
        {
            '$match': {
                'address.location': {
                    '$geoWithin': {
                        '$centerSphere': [
                            [
                                -157.8583, 21.3069
                            ], 0.0847
                        ]
                    }
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'name': 1,
                'islandName': '$address.market',
                'price': 1
            }
        }
    ])

    data.append(result)


    # ===== Задача 3 =====
    task_statement.append(
        'Задачи 3: Дополнение предыдущей задачи: найти все острова, где есть предложения по недвижимости'
    )

    # ----- в result подставляем решение из mongodb -----
    result = client['sample_airbnb']['listingsAndReviews'].aggregate([
        {
            '$match': {
                'address.location': {
                    '$geoWithin': {
                        '$centerSphere': [
                            [
                                -157.8583, 21.3069
                            ], 0.0847
                        ]
                    }
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'name': 1,
                'islandName': '$address.market',
                'price': 1
            }
        }, {
            '$match': {
                'islandName': {
                    '$nin': [
                        'Other (Domestic)', ''
                    ]
                }
            }
        }, {
            '$group': {
                '_id': None,
                'islands': {
                    '$addToSet': '$islandName'
                }
            }
        }, {
            '$project': {
                '_id': 0,
                'острова': {
                    '$reduce': {
                        'input': '$islands',
                        'initialValue': '',
                        'in': {
                            '$cond': [
                                {
                                    '$eq': [
                                        '$$value', ''
                                    ]
                                }, {
                                    '$toString': '$$this'
                                }, {
                                    '$concat': [
                                        '$$value', '\n', {
                                            '$toString': '$$this'
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }
    ])

    data.append(result)


    # ===== Задача 4 =====
    task_statement.append(
        'Условие задачи 4'
    )

    # ----- в result подставляем решение из mongodb -----
    result = ''

    data.append(result)



    """ *************** Блок вывода всех результатов на печать *************** """

    if len(data) != len(task_statement):
        raise IndexError("Ошибка!!! Кол-во заданий НЕ РАВНО кол-ву решений!!!")

    # Цикл по задачам
    for task_num, result in enumerate(data):
        print(50 * '=')
        print(task_statement[task_num])
        print()

        # Цикл по выводу документов решения
        docs = list(result)
        for idx, doc in enumerate(docs[:TIMES]):
            # print(idx, 50 * '-')
            pprint(doc)

        print(f"Total: {len(docs)} docs")
