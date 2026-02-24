## Шаг 1: Регистрация и получение API-ключа

1. Перейдите на сайт **OpenWeatherMap**: [https://openweathermap.org](https://openweathermap.org)
2. Зарегистрируйтесь или войдите в свой аккаунт.
3. Перейдите в раздел **API keys**: [https://home.openweathermap.org/api_keys](https://home.openweathermap.org/api_keys)
4. Нажмите **“Create key”** и дайте ключу имя (например, `Default`).
5. После создания ключ появится в списке. Скопируйте его.

   * Убедитесь, что статус ключа **Active**.
   * ⚠️Обратите внимание: 
     * **новые ключи могут работать не сразу** — иногда требуется 10–15 минут активации.

6. Добавляем ключ API в файл `local_settings.py`

```python
API = "4c8395c185b10e4e802b1ea2af0bc9c78"
```
---

## Шаг 2: Выбор правильного API

Для получения текущей погоды используем эндпойнт:

```
https://api.openweathermap.org/data/2.5/weather
```

Параметры запроса:

| Параметр | Обязателен | Пример          | Описание                                                    |
| -------- | ---------- | --------------- | ----------------------------------------------------------- |
| `q`      | ✅          | `"Moscow,RU"`   | Название города и код страны (RU, US и т.д.)                |
| `appid`  | ✅          | `"ваш_API_KEY"` | Ваш API-ключ                                                |
| `units`  | ❌          | `"metric"`      | Единицы измерения: metric (°C), imperial (°F), standard (K) |
| `lang`   | ❌          | `"ru"`          | Язык описания погоды (en, ru, etc.)                         |

Пример полного URL:

```
https://api.openweathermap.org/data/2.5/weather?q=Moscow,RU&appid=ВАШ_API_KEY&units=metric&lang=ru
```

---

## Шаг 3: Пример запроса `httpx`

```python
import httpx
from local_settings import API_KEY

city = "Moscow"
url = "https://api.openweathermap.org/data/2.5/weather"

params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "ru"}

response = httpx.get(url, params=params)
print(response.status_code)
print(response.text)
```

Если всё ОК, должно вернуться что-то вроде этого:

```json
{
  "coord": {
    "lon": 37.6156,
    "lat": 55.7522
  },
  "weather": [
    {
      "id": 804,
      "main": "Clouds",
      "description": "overcast clouds",
      "icon": "04n"
    }
  ],
  "base": "stations",
  "main": {
    "temp": -12.86,
    "feels_like": -19.86,
    "temp_min": -14.23,
    "temp_max": -12.41,
    "pressure": 1005,
    "humidity": 64,
    "sea_level": 1005,
    "grnd_level": 984
  },
  "visibility": 10000,
  "wind": {
    "speed": 6.09,
    "deg": 347,
    "gust": 15.16
  },
  "clouds": {
    "all": 100
  },
  "dt": 1771279080,
  "sys": {
    "type": 2,
    "id": 2094500,
    "country": "RU",
    "sunrise": 1771303826,
    "sunset": 1771339018
  },
  "timezone": 10800,
  "id": 524901,
  "name": "Moscow",
  "cod": 200
}
```

---

## Шаг 4: Проверка ошибок

* **401 Invalid API key** — ключ неверный, не активен или ещё не вступил в силу.
* **404 city not found** — город указан неверно, добавьте код страны: `"Moscow,RU"`.
* **429 Too many requests** — превышен лимит бесплатного API.


