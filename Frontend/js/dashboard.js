/**
 * WeatherIQ - Overview Dashboard Controller
 */

async function loadDashboard(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const subtitle = document.getElementById('dashboardCity');
  if (subtitle) subtitle.textContent = `Telemetry and forecast overview for ${city}`;
  updateFlowStep('flowProvider', `Requesting live conditions for ${city}…`, false);
  updateFlowStep('flowObservation', 'Waiting for current conditions', false);
  updateFlowStep('flowForecast', 'Waiting for forecast data', false);
  updateFlowStep('flowVisuals', 'Charts and map update when data arrives', false);

  try {
    // 1. Fetch Current Weather
    const currentRes = await window.weatherApp.fetchAPI(`/weather/current?city=${encodeURIComponent(city)}`);
    if (currentRes && currentRes.data) {
      updateCurrentWeather(currentRes.data);
      if (subtitle) subtitle.textContent = `Telemetry and forecast overview for ${city} · ${currentRes.data.source}`;
    }
  } catch (err) {
    console.warn('Current weather fetch notice:', err.message);
    const condEl = document.getElementById('currentCondition');
    if (condEl) condEl.textContent = `Weather data unavailable: ${err.message}`;
    updateFlowStep('flowProvider', `Live data unavailable: ${err.message}`, false);
    updateFlowStep('flowObservation', 'No current conditions received', false);
  }

  try {
    // 2. Fetch 5-day / 3-hour forecast for charts
    const forecastRes = await window.weatherApp.fetchAPI(`/weather/forecast?city=${encodeURIComponent(city)}&days=5`);
    if (forecastRes && forecastRes.data) {
      updateCharts(forecastRes.data);
    } else {
      updateFlowStep('flowForecast', 'No forecast data returned by the provider', false);
    }
  } catch (err) {
    console.warn('Forecast fetch notice:', err.message);
    updateFlowStep('flowForecast', `Forecast unavailable: ${err.message}`, false);
    updateFlowStep('flowVisuals', 'Charts could not be refreshed without forecast data', false);
  }

  // 3. Update Favorites & Recents
  updateRecentCitiesList();
  loadFavorites();

  const footerRefresh = document.getElementById('footerRefresh');
  if (footerRefresh) {
    footerRefresh.textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
  }
}

function updateCurrentWeather(data) {
  const icon = window.weatherApp.getWeatherIcon(data.weather_icon);
  const provider = data.source || 'Live weather provider';
  updateFlowStep('flowProvider', `${provider} · ${data.city || 'Selected city'}`, true);
  updateFlowStep(
    'flowObservation',
    `${window.weatherApp.formatTemperature(data.temperature)} · Humidity ${data.humidity ?? '--'}% · Wind ${window.weatherApp.formatWindSpeed(data.wind_speed)}`,
    true
  );

  // Hero Card
  const iconLg = document.getElementById('weatherIconLg');
  if (iconLg) iconLg.textContent = icon;

  const currentTemp = document.getElementById('currentTemp');
  if (currentTemp) currentTemp.textContent = window.weatherApp.formatTemperature(data.temperature);

  const currentCond = document.getElementById('currentCondition');
  if (currentCond) currentCond.textContent = data.weather_description || data.weather_main || '--';

  const feelsLike = document.getElementById('feelsLike');
  if (feelsLike) feelsLike.textContent = `Feels like ${window.weatherApp.formatTemperature(data.feels_like)}`;

  const currentLoc = document.getElementById('currentLocation');
  if (currentLoc) currentLoc.textContent = `${data.city || '--'}, ${data.country || ''}`;

  const currentDt = document.getElementById('currentDateTime');
  if (currentDt) currentDt.textContent = window.weatherApp.formatDateTime(data.observed_at);

  const lastUpdated = document.getElementById('lastUpdated');
  if (lastUpdated) lastUpdated.textContent = `Updated: ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  // Metric Cards
  const tempMinMax = document.getElementById('tempMinMax');
  if (tempMinMax) {
    tempMinMax.textContent = `${window.weatherApp.formatTemperature(data.temp_min)} / ${window.weatherApp.formatTemperature(data.temp_max)}`;
  }

  const humidity = document.getElementById('humidity');
  if (humidity) humidity.innerHTML = `${data.humidity ?? '--'}<span class="unit">%</span>`;

  const humidityDesc = document.getElementById('humidityDesc');
  if (humidityDesc) {
    const h = data.humidity;
    humidityDesc.textContent = h == null ? 'No humidity data' : h > 70 ? 'High humidity' : h < 30 ? 'Dry air' : 'Comfortable range';
  }

  const windSpeed = document.getElementById('windSpeed');
  if (windSpeed) windSpeed.textContent = window.weatherApp.formatWindSpeed(data.wind_speed);

  const windDir = document.getElementById('windDir');
  if (windDir) windDir.textContent = data.wind_direction && data.wind_deg != null
    ? `Direction: ${data.wind_direction} (${data.wind_deg}°)`
    : 'Direction: --';

  const pressure = document.getElementById('pressure');
  if (pressure) pressure.innerHTML = `${data.pressure ?? '--'}<span class="unit"> hPa</span>`;

  const pressureDesc = document.getElementById('pressureDesc');
  if (pressureDesc) {
    const p = data.pressure;
    pressureDesc.textContent = p == null ? 'No pressure data' : p < 1005 ? 'Low pressure (Precipitation risk)' : p > 1020 ? 'High pressure (Fair weather)' : 'Normal range';
  }

  const visibility = document.getElementById('visibility');
  if (visibility) {
    const visKm = data.visibility ? (data.visibility / 1000).toFixed(1) : '--';
    visibility.innerHTML = `${visKm}<span class="unit"> km</span>`;
  }

  const sunrise = document.getElementById('sunrise');
  if (sunrise) sunrise.textContent = data.sunrise ? new Date(data.sunrise).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

  const sunset = document.getElementById('sunset');
  if (sunset) sunset.textContent = data.sunset ? new Date(data.sunset).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

  const uvIndex = document.getElementById('uvIndex');
  if (uvIndex) uvIndex.textContent = data.uv_index == null ? '--' : data.uv_index;

  const aqiValue = document.getElementById('aqiValue');
  if (aqiValue) aqiValue.textContent = data.air_quality_index == null ? '--' : `US AQI ${data.air_quality_index}`;

  const cloudCover = document.getElementById('cloudCover');
  if (cloudCover) cloudCover.innerHTML = `${data.clouds ?? '--'}<span class="unit">%</span>`;
  const cloudDesc = document.getElementById('cloudDesc');
  if (cloudDesc) {
    cloudDesc.textContent = data.clouds == null
      ? 'Cloud cover unavailable from provider'
      : `${data.clouds <= 10 ? 'Mostly clear' : data.clouds <= 50 ? 'Partly cloudy' : 'Cloudy'} · ${data.source || 'Live weather data'}`;
  }

  const rainfall = document.getElementById('rainfall');
  if (rainfall) rainfall.innerHTML = `${data.rainfall ?? '--'}<span class="unit"> mm</span>`;
  const rainfallDesc = document.getElementById('rainfallDesc');
  if (rainfallDesc) {
    rainfallDesc.textContent = data.rainfall == null
      ? 'Current-hour precipitation unavailable'
      : data.rainfall === 0
        ? `No precipitation in the current hour · ${data.source || 'Live weather data'}`
        : `Current-hour precipitation · ${data.source || 'Live weather data'}`;
  }

  // Leaflet Mini Map
  if (data.lat && data.lon) {
    window.weatherMap.initMap('dashboardMap', [data.lat, data.lon], 9);
    window.weatherMap.clearMap('dashboardMap');
    window.weatherMap.addWeatherMarker(
      'dashboardMap',
      data.lat,
      data.lon,
      data.city,
      window.weatherApp.formatTemperature(data.temperature),
      data.weather_description || data.weather_main,
      icon
    );
  }
}

function updateCharts(forecastData) {
  const items = forecastData.forecast || [];
  const hourlyStatus = document.getElementById('hourlyChartStatus');
  const forecastStatus = document.getElementById('forecastChartStatus');
  if (!items.length) {
    if (hourlyStatus) hourlyStatus.textContent = 'No forecast points available to plot.';
    if (forecastStatus) forecastStatus.textContent = 'No forecast points available to plot.';
    updateFlowStep('flowForecast', 'Provider returned no forecast points', false);
    updateFlowStep('flowVisuals', 'Waiting for forecast data before drawing charts', false);
    return;
  }

  // 1. Next 24 Hours (approx 8 intervals of 3-hours)
  const next24 = items.slice(0, 8);
  const hourlyLabels = next24.map(i => {
    const d = new Date(i.dt_txt);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  });
  const hourlyTemps = next24.map(i => i.temperature);
  window.weatherCharts.renderHourlyTemp('tempChart24h', hourlyLabels, hourlyTemps);
  if (hourlyStatus) hourlyStatus.textContent = `${next24.length} forecast points · ${forecastData.source || 'Live forecast'}`;

  // 2. 5-Day Trend
  // Group by day
  const dailyMap = {};
  items.forEach(i => {
    const dateKey = (i.dt_txt || i.forecast_dt || '').slice(0, 10);
    if (!dateKey) return;
    const day = new Date(`${dateKey}T12:00:00`).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    if (!dailyMap[day]) {
      dailyMap[day] = { temps: [], rain: [] };
    }
    if (Number.isFinite(i.temperature)) dailyMap[day].temps.push(i.temperature);
    if (Number.isFinite(i.rainfall_prob)) {
      dailyMap[day].rain.push(i.rainfall_prob <= 1 ? i.rainfall_prob * 100 : i.rainfall_prob);
    }
  });

  const dayLabels = Object.keys(dailyMap).slice(0, 5);
  const avgTemps = dayLabels.map(d => {
    const arr = dailyMap[d].temps;
    return arr.length ? Math.round((arr.reduce((a, b) => a + b, 0) / arr.length) * 10) / 10 : null;
  });
  const avgRain = dayLabels.map(d => {
    const arr = dailyMap[d].rain;
    return arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : null;
  });

  window.weatherCharts.render5DayForecast('forecastChart5d', dayLabels, avgTemps, avgRain);
  if (forecastStatus) forecastStatus.textContent = `${dayLabels.length} forecast days · Temperature and precipitation probability`;
  updateFlowStep('flowForecast', `${items.length} forecast points across ${dayLabels.length} days · ${forecastData.source || 'Live forecast'}`, true);
  updateFlowStep('flowVisuals', `Updated ${next24.length} hourly points, ${dayLabels.length} daily summaries and the city map`, true);
}

function updateFlowStep(stepId, detail, isComplete) {
  const step = document.getElementById(stepId);
  const detailEl = document.getElementById(`${stepId}Detail`);
  if (detailEl) detailEl.textContent = detail;
  if (step) step.classList.toggle('is-complete', isComplete);
}

function updateRecentCitiesList() {
  const container = document.getElementById('recentCities');
  if (!container) return;

  const recents = window.weatherApp.getRecentCities();
  if (!recents.length) {
    container.innerHTML = '<div class="empty-state" style="padding:15px;"><div class="empty-state-desc">No searches yet</div></div>';
    return;
  }

  container.innerHTML = `
    <div style="display:flex; flex-wrap:wrap; gap:8px;">
      ${recents.map(c => `
        <button class="btn btn-sm btn-outline-secondary" onclick="window.weatherApp.handleCitySearch('${c}')" style="background:#fff; border:1px solid #dbe2ea; color:#1f2937; border-radius:6px; padding:4px 10px; cursor:pointer;">
          📍 ${c}
        </button>
      `).join('')}
    </div>
  `;
}

async function loadFavorites() {
  const container = document.getElementById('favoriteCities');
  if (!container) return;

  try {
    const res = await window.weatherApp.fetchAPI('/settings/favorites');
    const favs = res.favorites || [];
    if (!favs.length) {
      container.innerHTML = '<div class="empty-state" style="padding:15px;"><div class="empty-state-desc">No favorites added yet. Add cities from settings.</div></div>';
      return;
    }

    container.innerHTML = favs.map(f => `
      <div style="display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid #dbe2ea;">
        <span style="font-weight:500; cursor:pointer;" onclick="window.weatherApp.handleCitySearch('${f.name}')">⭐ ${f.name}</span>
        <button class="btn btn-sm" onclick="window.weatherApp.handleCitySearch('${f.name}')" style="background:#2563eb; color:#fff; border:none; padding:2px 8px; border-radius:4px; font-size:12px;">View</button>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div class="text-muted" style="padding:10px;">Failed to load favorites</div>';
  }
}

// Hook for city searches & auto refresh
window.reloadCurrentPageData = function(city) {
  loadDashboard(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
});
