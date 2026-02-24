Если предыдущий запрос увенчался успехом, добавляем запрос погоды в наш проект.

Для простоты - просто добавим код в модуль `main.py`

```python
# -----------------------------
# 3. OpenWeatherMap.com
# -----------------------------

# 3.1. ------------ Pydentic model --------------------

from pydantic import BaseModel
from typing import List, Optional

class WeatherDetails(BaseModel):
    main: str
    description: str

class Wind(BaseModel):
    speed: float
    deg: int
    gust: Optional[float]

class Clouds(BaseModel):
    all: int

class SysInfo(BaseModel):
    country: str
    sunrise: int
    sunset: int

class WeatherResponse(BaseModel):
    city: str
    temperature: float
    description: str
    wind: Wind
    clouds: Clouds
    sys: SysInfo


# 3.2. ------------ weather_service --------------------

from locaskAPI_KEY 
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

async def fetch_weather_data(city: str) -> WeatherResponse:
    """
    Отправляет запрос в OpenWeatherMap API для получения данных о погоде.
    """
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",  # Получаем температуру в Цельсиях
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            return WeatherResponse(
                city=data["name"],
                temperature=data["main"]["temp"],
                description=data["weather"][0]["description"],
                wind=data["wind"],
                clouds=data["clouds"],
                sys=data["sys"]
            )
        else:
            raise Exception(f"Ошибка при получении данных: {response.text}")


# 3.3. ------------ api endpoint -------------------

from fastapi import HTTPException
from httpx import HTTPStatusError


@app.get("/api/{city}", response_model=WeatherResponse)
async def get_weather(city: str):
    """
    Получает текущую погоду для указанного города.
    """
    try:
        weather_data = await fetch_weather_data(city)
        return weather_data
    except HTTPStatusError as e:
        # Получаем статус и текст ответа
        status = e.response.status_code
        text = e.response.text

        if status == 401:
            raise HTTPException(status_code=401, detail="Неверный API-ключ. Проверьте ключ и попробуйте снова.")
        elif status == 404:
            raise HTTPException(status_code=404, detail=f"Город '{city}' не найден.")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Превышен лимит запросов к API OpenWeatherMap.")
        else:
            raise HTTPException(status_code=status, detail=f"Ошибка OpenWeatherMap: {text}")

    except Exception as e:
        # Все остальные ошибки
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

```
