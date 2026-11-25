"""
config.example.py
------------------
Template for config.py. Copy this file to config.py and fill in your
own MySQL credentials and OpenWeatherMap API key. config.py is
git-ignored so your real secrets never get committed.
"""

# ---- MySQL connection settings ----
DB_CONFIG = {
    "host": "localhost",
    "user": "root",          # change to your MySQL username
    "password": "",          # change to your MySQL password
    "database": "weather_aqi_db",
}

# ---- OpenWeatherMap API ----
OWM_API_KEY = "your-openweathermap-api-key"

# OpenWeatherMap endpoints used by app.py
GEO_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
AIR_POLLUTION_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
