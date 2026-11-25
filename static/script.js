/* ============================================================
   Weather & AQI Monitor - frontend logic
   Talks to the Flask backend (app.py), which in turn talks to
   OpenWeatherMap and MySQL. This file never calls OWM directly.
   ============================================================ */

const cityInput   = document.getElementById("cityInput");
const searchBtn    = document.getElementById("searchBtn");
const errorMsg     = document.getElementById("errorMsg");
const resultSection = document.getElementById("resultSection");
const citySelect   = document.getElementById("citySelect");
const historyBody  = document.getElementById("historyBody");

// Names + units shown for each pollutant returned by the API
const POLLUTANTS = [
  ["co", "CO"], ["no", "NO"], ["no2", "NO₂"], ["o3", "O₃"],
  ["so2", "SO₂"], ["pm2_5", "PM2.5"], ["pm10", "PM10"], ["nh3", "NH₃"],
];

// ---- Search button: fetch live data + save to DB ----
searchBtn.addEventListener("click", searchCity);
cityInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") searchCity();
});

async function searchCity() {
  const city = cityInput.value.trim();
  if (!city) return;

  hideError();
  searchBtn.disabled = true;
  searchBtn.textContent = "Searching...";

  try {
    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ city }),
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }

    renderResult(data);
    await loadCityList(city);       // refresh dropdown (new city may have been added)
  } catch (err) {
    showError("Could not reach the server. Is app.py running?");
  } finally {
    searchBtn.disabled = false;
    searchBtn.textContent = "Search";
  }
}

// ---- Render the current weather + AQI cards ----
function renderResult(data) {
  document.getElementById("cityTitle").textContent = `${data.city}, ${data.country}`;
  document.getElementById("weatherDesc").textContent = data.weather_desc;
  document.getElementById("temperature").textContent = `${data.temperature}°C`;
  document.getElementById("feelsLike").textContent = `Feels like ${data.feels_like}°C`;
  document.getElementById("humidity").textContent = `${data.humidity}%`;
  document.getElementById("pressure").textContent = `${data.pressure} hPa`;
  document.getElementById("wind").textContent = `${data.wind_speed} m/s`;

  const badge = document.getElementById("aqiBadge");
  badge.textContent = `AQI ${data.aqi} - ${data.aqi_label}`;
  badge.dataset.level = data.aqi;

  const grid = document.getElementById("pollutantGrid");
  grid.innerHTML = POLLUTANTS.map(([key, label]) => `
    <div class="pollutant">
      <span>${label}</span>
      <span>${data.components[key]} µg/m³</span>
    </div>
  `).join("");

  resultSection.classList.remove("hidden");
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove("hidden");
  resultSection.classList.add("hidden");
}
function hideError() {
  errorMsg.classList.add("hidden");
}

// ---- City dropdown for history lookup ----
citySelect.addEventListener("change", () => {
  if (citySelect.value) loadHistory(citySelect.value);
});

async function loadCityList(selectCityName) {
  const res = await fetch("/api/cities");
  const cities = await res.json();

  citySelect.innerHTML = '<option value="">Select a searched city...</option>' +
    cities.map(c => `<option value="${c.city_id}">${c.city_name}, ${c.country}</option>`).join("");

  // auto-select the city that was just searched, and load its history
  if (selectCityName) {
    const match = cities.find(c => c.city_name.toLowerCase() === selectCityName.toLowerCase());
    if (match) {
      citySelect.value = match.city_id;
      loadHistory(match.city_id);
    }
  }
}

async function loadHistory(cityId) {
  const res = await fetch(`/api/history/${cityId}`);
  const rows = await res.json();

  if (rows.length === 0) {
    historyBody.innerHTML = '<tr><td colspan="7" class="empty-row">No history for this city yet.</td></tr>';
    return;
  }

  historyBody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.recorded_at}</td>
      <td>${r.temperature}</td>
      <td>${r.humidity}%</td>
      <td>${r.weather_desc}</td>
      <td>${r.aqi} (${r.aqi_label})</td>
      <td>${r.pm2_5}</td>
      <td>${r.pm10}</td>
    </tr>
  `).join("");
}

// ---- Load the city dropdown once on page load ----
loadCityList();
