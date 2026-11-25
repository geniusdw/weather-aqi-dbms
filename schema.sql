-- ============================================================
-- Weather & AQI Monitoring System - Database Schema (MySQL)
-- DBMS Mini Project
-- ============================================================
-- Run this once in MySQL to create the database and tables:
--   mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS weather_aqi_db;
USE weather_aqi_db;

-- ------------------------------------------------------------
-- Table 1: cities
-- Stores each unique city that has been searched, along with
-- its geo-coordinates (fetched once from OpenWeatherMap Geocoding API).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cities (
    city_id     INT AUTO_INCREMENT PRIMARY KEY,
    city_name   VARCHAR(100) NOT NULL,
    country     VARCHAR(10),
    latitude    DECIMAL(9,6) NOT NULL,
    longitude   DECIMAL(9,6) NOT NULL,
    UNIQUE KEY uq_city_country (city_name, country)   -- avoid duplicate city rows
);

-- ------------------------------------------------------------
-- Table 2: weather_data
-- Stores a weather reading (temperature, humidity, etc.) for a
-- city at the time it was fetched. One city can have MANY readings
-- over time -> classic 1-to-many relationship.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_data (
    weather_id      INT AUTO_INCREMENT PRIMARY KEY,
    city_id         INT NOT NULL,
    temperature     DECIMAL(5,2),   -- in Celsius
    feels_like      DECIMAL(5,2),
    humidity        INT,            -- in %
    pressure        INT,            -- in hPa
    wind_speed      DECIMAL(5,2),   -- in m/s
    weather_main    VARCHAR(50),    -- e.g. "Clouds", "Rain"
    weather_desc    VARCHAR(150),   -- e.g. "scattered clouds"
    recorded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Table 3: aqi_data
-- Stores an Air Quality Index reading (pollutant concentrations)
-- for a city at the time it was fetched. Also 1-to-many with cities.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aqi_data (
    aqi_id          INT AUTO_INCREMENT PRIMARY KEY,
    city_id         INT NOT NULL,
    aqi             INT,            -- OpenWeatherMap scale: 1(Good) - 5(Very Poor)
    co              DECIMAL(8,2),   -- Carbon monoxide, ug/m3
    no              DECIMAL(8,2),   -- Nitrogen monoxide
    no2             DECIMAL(8,2),   -- Nitrogen dioxide
    o3              DECIMAL(8,2),   -- Ozone
    so2             DECIMAL(8,2),   -- Sulphur dioxide
    pm2_5           DECIMAL(8,2),   -- Fine particulate matter
    pm10            DECIMAL(8,2),   -- Coarse particulate matter
    nh3             DECIMAL(8,2),   -- Ammonia
    recorded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id) ON DELETE CASCADE
);

-- Helpful indexes for faster history lookups by city + time
CREATE INDEX idx_weather_city_time ON weather_data(city_id, recorded_at);
CREATE INDEX idx_aqi_city_time ON aqi_data(city_id, recorded_at);
