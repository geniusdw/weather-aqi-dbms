"""
app.py
------
Flask backend for the Weather & AQI DBMS mini project.

Flow for a search:
  1. User types a city name in the UI -> POST /api/search
  2. We call OWM Geocoding API to get lat/lon for the city
  3. We call OWM Current Weather API + Air Pollution API using lat/lon
  4. We INSERT/UPDATE the city in `cities`, then INSERT new rows into
     `weather_data` and `aqi_data` (this is how history builds up)
  5. We return the fresh reading as JSON for the frontend to render

Other endpoints let the UI list previously-searched cities and fetch
their stored history from MySQL.
"""

import requests
from flask import Flask, jsonify, render_template, request
import mysql.connector

from config import AIR_POLLUTION_URL, DB_CONFIG, GEO_URL, OWM_API_KEY, WEATHER_URL

app = Flask(__name__)

# AQI number (1-5) -> human readable label, per OpenWeatherMap's scale
AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}


def get_db_connection():
    """Open a fresh MySQL connection using settings from config.py."""
    return mysql.connector.connect(**DB_CONFIG)


def get_or_create_city(cursor, city_name, country, lat, lon):
    """
    Return city_id for (city_name, country), inserting a new row
    if this city hasn't been searched before. Keeps `cities` free
    of duplicates (unique key on city_name + country handles races).
    """
    cursor.execute(
        "SELECT city_id FROM cities WHERE city_name = %s AND country = %s",
        (city_name, country),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO cities (city_name, country, latitude, longitude) "
        "VALUES (%s, %s, %s, %s)",
        (city_name, country, lat, lon),
    )
    return cursor.lastrowid


@app.route("/")
def index():
    """Serve the frontend page."""
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search_city():
    """
    Body: { "city": "Pune" }
    Fetches live weather + AQI for the city from OpenWeatherMap,
    stores the reading in MySQL, and returns it as JSON.
    """
    city_name = request.get_json(silent=True, force=True).get("city", "").strip()
    if not city_name:
        return jsonify({"error": "Please enter a city name."}), 400

    # 1) Geocode the city name -> latitude / longitude
    geo_resp = requests.get(
        GEO_URL, params={"q": city_name, "limit": 1, "appid": OWM_API_KEY}
    ).json()

    if not geo_resp:
        return jsonify({"error": f"City '{city_name}' not found."}), 404

    place = geo_resp[0]
    lat, lon = place["lat"], place["lon"]
    resolved_name = place["name"]
    country = place.get("country", "")

    # 2) Current weather for those coordinates
    weather = requests.get(
        WEATHER_URL,
        params={"lat": lat, "lon": lon, "units": "metric", "appid": OWM_API_KEY},
    ).json()

    # 3) Air pollution / AQI for the same coordinates
    air = requests.get(
        AIR_POLLUTION_URL, params={"lat": lat, "lon": lon, "appid": OWM_API_KEY}
    ).json()
    air_item = air["list"][0]

    # 4) Save everything to MySQL
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        city_id = get_or_create_city(cursor, resolved_name, country, lat, lon)

        cursor.execute(
            """INSERT INTO weather_data
               (city_id, temperature, feels_like, humidity, pressure,
                wind_speed, weather_main, weather_desc)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                city_id,
                weather["main"]["temp"],
                weather["main"]["feels_like"],
                weather["main"]["humidity"],
                weather["main"]["pressure"],
                weather["wind"]["speed"],
                weather["weather"][0]["main"],
                weather["weather"][0]["description"],
            ),
        )

        comp = air_item["components"]
        cursor.execute(
            """INSERT INTO aqi_data
               (city_id, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                city_id,
                air_item["main"]["aqi"],
                comp["co"], comp["no"], comp["no2"], comp["o3"],
                comp["so2"], comp["pm2_5"], comp["pm10"], comp["nh3"],
            ),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    # 5) Build the JSON response the frontend expects
    aqi_value = air_item["main"]["aqi"]
    return jsonify({
        "city": resolved_name,
        "country": country,
        "temperature": weather["main"]["temp"],
        "feels_like": weather["main"]["feels_like"],
        "humidity": weather["main"]["humidity"],
        "pressure": weather["main"]["pressure"],
        "wind_speed": weather["wind"]["speed"],
        "weather_main": weather["weather"][0]["main"],
        "weather_desc": weather["weather"][0]["description"],
        "aqi": aqi_value,
        "aqi_label": AQI_LABELS.get(aqi_value, "Unknown"),
        "components": comp,
    })


@app.route("/api/cities")
def list_cities():
    """Return every city stored so far, for the history dropdown."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT city_id, city_name, country FROM cities ORDER BY city_name")
    cities = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(cities)


@app.route("/api/history/<int:city_id>")
def city_history(city_id):
    """
    Return the last 10 stored (weather + AQI) readings for a city,
    newest first. Demonstrates a JOIN across weather_data and aqi_data
    on their shared city_id and matching timestamps.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT w.recorded_at, w.temperature, w.humidity, w.weather_desc,
               a.aqi, a.pm2_5, a.pm10
        FROM weather_data w
        JOIN aqi_data a
          ON w.city_id = a.city_id
         AND ABS(TIMESTAMPDIFF(SECOND, w.recorded_at, a.recorded_at)) < 5
        WHERE w.city_id = %s
        ORDER BY w.recorded_at DESC
        LIMIT 10
        """,
        (city_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # datetime objects aren't JSON serialisable by default -> convert to string
    for row in rows:
        row["recorded_at"] = row["recorded_at"].strftime("%Y-%m-%d %H:%M:%S")
        row["aqi_label"] = AQI_LABELS.get(row["aqi"], "Unknown")

    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True)
