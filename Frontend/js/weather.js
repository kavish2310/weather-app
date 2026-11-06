/**
 * WeatherIQ - Live Weather & Comparison Page Controller
 */

let comparisonCities = ['Indore', 'Mumbai', 'New Delhi'];

async function loadWeatherPage(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const subtitle = document.getElementById('weatherPageCity');
  if (subtitle) subtitle.textContent = `High-precision telemetry and multiday forecast for ${city}`;

  try {
    const res = await window.weatherApp.fetchAPI(`/weather/current?city=${encodeURIComponent(city)}`);
    if (res && res.data) {
      renderWeatherDetails(res.data);
      if (subtitle) {
        subtitle.textContent = `Live weather for ${res.data.city} · Data: ${res.data.source || 'unknown source'}`;
      }
    }
  } catch (err) {
    console.error('Weather page error:', err);
    if (subtitle) subtitle.textContent = `Live weather unavailable: ${err.message}`;
  }

  try {
    const fRes = await window.weatherApp.fetchAPI(`/weather/forecast?city=${encodeURIComponent(city)}&days=5`);
    if (fRes && fRes.data) {
      renderHourlyCards(fRes.data);
      renderDailyForecast(fRes.data);
    }
  } catch (err) {
    console.error('Forecast fetch error:', err);
    const hourly = document.getElementById('hourlyForecast');
    const daily = document.getElementById('dailyForecast');
    if (hourly) hourly.innerHTML = `<div class="empty-state">Forecast unavailable: ${err.message}</div>`;
    if (daily) daily.innerHTML = `<div class="empty-state">Forecast unavailable: ${err.message}</div>`;
  }

  loadComparison();
}

function renderWeatherDetails(data) {
  const icon = window.weatherApp.getWeatherIcon(data.weather_icon);

  // Match both weatherIconLg and liveWeatherIcon
  const heroIcon = document.getElementById('weatherIconLg') || document.getElementById('liveWeatherIcon');
  if (heroIcon) heroIcon.textContent = icon;

  const heroTemp = document.getElementById('currentTemp') || document.getElementById('liveTemp');
  if (heroTemp) heroTemp.textContent = window.weatherApp.formatTemperature(data.temperature);

  const heroCond = document.getElementById('currentCondition') || document.getElementById('liveCondition');
  if (heroCond) heroCond.textContent = data.weather_description || data.weather_main || 'Clear sky';

  const heroFeels = document.getElementById('feelsLike') || document.getElementById('liveFeelsLike');
  if (heroFeels) heroFeels.textContent = `Feels like ${window.weatherApp.formatTemperature(data.feels_like)}`;

  const heroLoc = document.getElementById('currentLocation') || document.getElementById('liveLocation');
  if (heroLoc) heroLoc.textContent = `${data.city || 'Indore'}, ${data.country || 'IN'}`;

  // Helper to safely set element text
  const setValue = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setValue('detailHumidity', data.humidity == null ? '--' : `${data.humidity}%`);
  setValue('detailWind', window.weatherApp.formatWindSpeed(data.wind_speed));
  setValue(
    'detailWindDir',
    data.wind_direction && data.wind_deg != null
      ? `${data.wind_direction} (${data.wind_deg}°)`
      : '--'
  );
  setValue('detailPressure', data.pressure == null ? '--' : `${data.pressure} hPa`);
  setValue('detailVisibility', data.visibility == null ? '--' : `${(data.visibility / 1000).toFixed(1)} km`);
  setValue('detailClouds', data.clouds == null ? '--' : `${data.clouds}%`);

  const sunriseStr = data.sunrise ? new Date(data.sunrise).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
  const sunsetStr = data.sunset ? new Date(data.sunset).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';
  setValue('detailSunrise', sunriseStr);
  setValue('detailSunset', sunsetStr);

  // Approximate dew point: T - (100 - RH)/5
  const dewPoint = data.temperature != null && data.humidity != null
    ? Math.round((data.temperature - ((100 - data.humidity) / 5)) * 10) / 10
    : null;
  setValue('detailDewPoint', window.weatherApp.formatTemperature(dewPoint));

  if (data.uv_index == null) {
    setValue('detailUV', '--');
  } else {
    const uvLabel = data.uv_index > 8 ? 'Very High' : data.uv_index > 5 ? 'High' : data.uv_index > 2 ? 'Moderate' : 'Low';
    setValue('detailUV', `${data.uv_index} (${uvLabel})`);
  }
}

function renderHourlyCards(forecastData) {
  // Support both container IDs
  const container = document.getElementById('hourlyForecast') || document.getElementById('hourlyScroll');
  if (!container) return;

  const items = (forecastData.forecast || forecastData.forecasts || []).slice(0, 12);
  if (!items.length) {
    container.innerHTML = '<div class="empty-state">No hourly data available</div>';
    return;
  }

  container.innerHTML = items.map(item => {
    const dt = new Date(item.dt_txt || item.forecast_dt);
    const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const dayStr = dt.toLocaleDateString([], { weekday: 'short' });
    const icon = window.weatherApp.getWeatherIcon(item.weather_icon);
    const temp = window.weatherApp.formatTemperature(item.temperature);

    const rawPop = item.rainfall_prob;
    const rainProbVal = rawPop == null ? '--' : rawPop > 1.0 ? Math.round(rawPop) : Math.round(rawPop * 100);

    return `
      <div style="flex:0 0 110px; background:var(--color-bg-tertiary); border:1px solid var(--color-border); border-radius:10px; padding:12px; text-align:center;">
        <div style="font-size:11px; color:var(--color-text-muted);">${dayStr}</div>
        <div style="font-weight:600; font-size:13px; margin-bottom:6px;">${timeStr}</div>
        <div style="font-size:24px; margin-bottom:6px;">${icon}</div>
        <div style="font-size:15px; font-weight:700;">${temp}</div>
        <div style="font-size:11px; color:var(--color-accent); margin-top:4px;">💧 ${rainProbVal}${rainProbVal === '--' ? '' : '%'}</div>
      </div>
    `;
  }).join('');
}

function renderDailyForecast(forecastData) {
  const container = document.getElementById('dailyForecast') || document.getElementById('dailyForecastList');
  if (!container) return;

  const items = forecastData.forecast || forecastData.forecasts || [];
  const days = {};
  items.forEach(i => {
    const rawDt = i.dt_txt || i.forecast_dt || '';
    const d = rawDt.split('T')[0].split(' ')[0];
    if (!days[d]) days[d] = [];
    days[d].push(i);
  });

  const dayKeys = Object.keys(days).slice(0, 5);
  container.innerHTML = dayKeys.map(dateKey => {
    const dayItems = days[dateKey];
    const dt = new Date(dateKey);
    const dayName = dt.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
    const temps = dayItems.map(x => x.temperature);
    const minTemp = Math.min(...temps);
    const maxTemp = Math.max(...temps);
    const midItem = dayItems[Math.floor(dayItems.length / 2)] || dayItems[0];
    const icon = window.weatherApp.getWeatherIcon(midItem.weather_icon);

    return `
      <div style="display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid var(--color-border);">
        <div style="min-width:140px; font-weight:500;">${dayName}</div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:22px;">${icon}</span>
          <span style="color:var(--color-text-muted); font-size:13px;">${midItem.weather_description}</span>
        </div>
        <div style="font-weight:600; min-width:120px; text-align:right;">
          <span style="color:var(--color-accent);">${window.weatherApp.formatTemperature(minTemp)}</span>
          <span style="color:var(--color-text-muted); margin: 0 4px;">/</span>
          <span style="color:#b45309;">${window.weatherApp.formatTemperature(maxTemp)}</span>
        </div>
      </div>
    `;
  }).join('');
}

async function loadComparison() {
  const container = document.getElementById('comparisonGrid');
  if (!container) return;

  try {
    const res = await window.weatherApp.fetchAPI(`/weather/multiple?cities=${encodeURIComponent(comparisonCities.join(','))}`);
    const citiesData = res.data && res.data.cities ? res.data.cities : [];

    if (!citiesData.length) {
      container.innerHTML = '<div class="empty-state">No comparison data available</div>';
      return;
    }

    container.innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
        ${citiesData.map(c => `
          <div class="card" style="margin:0; border:1px solid var(--color-border);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <h5 style="margin:0; font-weight:600;">${c.city}</h5>
              <button onclick="removeComparisonCity('${c.city}')" style="background:none; border:none; color:#ef4444; cursor:pointer;">✕</button>
            </div>
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
              <span style="font-size:32px;">${window.weatherApp.getWeatherIcon(c.weather_icon)}</span>
              <div>
                <div style="font-size:22px; font-weight:700;">${window.weatherApp.formatTemperature(c.temperature)}</div>
                <div style="font-size:12px; color:var(--color-text-muted);">${c.weather_description}</div>
              </div>
            </div>
            <div style="font-size:12px; color:var(--color-text-muted); line-height:1.7;">
              <div>💧 Humidity: <strong style="color:var(--color-text-primary);">${c.humidity}%</strong></div>
              <div>💨 Wind: <strong style="color:var(--color-text-primary);">${window.weatherApp.formatWindSpeed(c.wind_speed)}</strong></div>
              <div>📊 Pressure: <strong style="color:var(--color-text-primary);">${c.pressure} hPa</strong></div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    console.warn('Comparison error:', err);
  }
}

function removeComparisonCity(name) {
  comparisonCities = comparisonCities.filter(c => c.toLowerCase() !== name.toLowerCase());
  loadComparison();
}

window.reloadCurrentPageData = function(city) {
  loadWeatherPage(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadWeatherPage();

  const addBtn = document.getElementById('addComparisonBtn');
  const input = document.getElementById('comparisonCityInput');
  if (addBtn && input) {
    addBtn.addEventListener('click', () => {
      const val = input.value.trim();
      if (val && !comparisonCities.map(c => c.toLowerCase()).includes(val.toLowerCase())) {
        comparisonCities.push(val);
        input.value = '';
        loadComparison();
      }
    });
  }
});
