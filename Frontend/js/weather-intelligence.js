(() => {
  'use strict';

  const API_BASE = `${window.location.origin}/api`;
  const fallbackAPI = 'http://127.0.0.1:5000/api';
  const getApiBase = () => window.location.protocol === 'file:' ? fallbackAPI : API_BASE;
  const state = {
    city: new URLSearchParams(window.location.search).get('city') ||
      localStorage.getItem('weatheriq_last_city') || 'Indore',
    weather: null,
    chart: null,
    mainMap: null,
    cycloneMap: null,
    weatherMarker: null,
    cycloneMarkers: [],
    overlayLayers: {},
    activeOverlay: null,
    requestId: 0
  };

  const $ = id => document.getElementById(id);
  const text = (id, value) => {
    const element = $(id);
    if (element) element.textContent = value == null || value === '' ? '--' : value;
  };
  const hasNumber = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const number = (value, digits = 0) => hasNumber(value) ? Number(value).toFixed(digits) : '--';

  async function fetchJSON(path) {
    const response = await fetch(`${getApiBase()}${path}`, {
      headers: { Accept: 'application/json' }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.error || body.message || `Request failed (${response.status})`);
    }
    return body;
  }

  function formatTime(value) {
    if (!value) return '--';
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? '--'
      : new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date);
  }

  function formatDate(value) {
    const date = value ? new Date(value) : new Date();
    return Number.isNaN(date.getTime())
      ? 'Local weather overview'
      : new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'short', day: 'numeric' }).format(date);
  }

  function setIcon(condition) {
    const element = $('wiWeatherIcon');
    if (!element) return;
    const normalized = String(condition || '').toLowerCase();
    const icon = normalized.includes('thunder') ? 'bi-cloud-lightning-rain-fill'
      : normalized.includes('rain') || normalized.includes('drizzle') ? 'bi-cloud-rain-fill'
        : normalized.includes('snow') ? 'bi-cloud-snow-fill'
          : normalized.includes('fog') ? 'bi-cloud-fog-fill'
            : normalized.includes('cloud') ? 'bi-cloud-sun-fill'
              : 'bi-sun-fill';
    element.innerHTML = `<i class="bi ${icon}" aria-hidden="true"></i>`;
    element.setAttribute('aria-label', condition || 'Weather');
  }

  function renderWeather(data) {
    if (!data || typeof data !== 'object') throw new Error('Weather provider returned no current conditions.');
    state.weather = data;
    state.city = data.city || state.city;
    text('wiCurrentCity', [data.city, data.country].filter(Boolean).join(', ') || state.city);
    text('wiCurrentDate', formatDate(data.observed_at));
    text('wiTemperature', number(data.temperature, 0));
    text('wiCondition', data.weather_description || data.weather_main || 'Condition unavailable');
    text('wiFeelsLike', hasNumber(data.feels_like) ? `Feels like ${number(data.feels_like, 0)}°C` : 'Feels-like temperature unavailable');
    text('wiWind', hasNumber(data.wind_speed)
      ? `${number(data.wind_speed, 1)} km/h${data.wind_direction ? ` ${data.wind_direction}` : ''}`
      : 'Unavailable');
    text('wiHumidity', hasNumber(data.humidity) ? `${number(data.humidity)}%` : 'Unavailable');
    text('wiPressure', hasNumber(data.pressure) ? `${number(data.pressure, 1)} hPa` : 'Unavailable');
    text('wiSunTimes', `${formatTime(data.sunrise)} / ${formatTime(data.sunset)}`);
    text('wiWeatherSource', data.source || 'Source not provided');
    text('wiDailyRange', `${number(data.temp_min, 0)}°  →  ${number(data.temp_max, 0)}°`);
    text('wiPrecipitation', hasNumber(data.rainfall) ? `${number(data.rainfall, 1)} mm` : 'Unavailable');
    text('wiCloudCover', hasNumber(data.clouds) ? `${number(data.clouds)}%` : 'Unavailable');
    text('wiLocationSubtitle', `Live conditions and weather insights for ${data.city || state.city}${data.country ? `, ${data.country}` : ''}.`);
    setIcon(data.weather_description || data.weather_main);
    updateMainMap(data);
  }

  function updateMainMap(weather) {
    if (!state.mainMap || !hasNumber(weather.lat) || !hasNumber(weather.lon)) return;
    const point = [Number(weather.lat), Number(weather.lon)];
    state.mainMap.setView(point, 8);
    if (state.weatherMarker) state.mainMap.removeLayer(state.weatherMarker);
    state.weatherMarker = L.marker(point, {
      icon: L.divIcon({ className: '', html: '<span class="wi-city-icon"></span>', iconSize: [15, 15], iconAnchor: [7, 7] })
    }).bindPopup(`<strong>${escapeHTML(weather.city || state.city)}</strong><br>${escapeHTML(number(weather.temperature, 1))}°C · ${escapeHTML(weather.weather_description || 'Current conditions')}`);
    state.weatherMarker.addTo(state.mainMap);
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
  }

  function renderAlerts(data) {
    const container = $('wiAlertList');
    const alerts = Array.isArray(data.alerts) ? data.alerts : [];
    text('wiAlertSummary', String(alerts.length));
    const badge = $('wiNotificationCount');
    if (badge) {
      badge.hidden = alerts.length === 0;
      badge.textContent = alerts.length > 9 ? '9+' : String(alerts.length);
    }
    if (!container) return;
    if (!alerts.length) {
      container.innerHTML = '<div class="wi-empty-state is-clear"><i class="bi bi-check-circle"></i><span>No active alerts reported for this city.</span></div>';
      return;
    }
    container.innerHTML = alerts.slice(0, 3).map(alert => `
      <div class="wi-alert-item">
        <span class="wi-alert-symbol"><i class="bi bi-exclamation-triangle"></i></span>
        <div class="wi-alert-copy">
          <strong>${escapeHTML(alert.title || alert.alert_type || 'Weather alert')}</strong>
          <p>${escapeHTML(alert.description || alert.affected_area || 'See alert details for official guidance.')}</p>
        </div>
        <span class="wi-alert-severity">${escapeHTML(alert.severity || 'Notice')}</span>
      </div>`).join('');
  }

  function parseForecastTime(item) {
    const value = item.dt_txt || item.forecast_dt || item.timestamp;
    const date = value ? new Date(String(value).replace(' ', 'T')) : null;
    return date && !Number.isNaN(date.getTime()) ? date : null;
  }

  function dayLabel(date) {
    return new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).format(date);
  }

  function renderTemperatureChart(historyPayload, forecastPayload) {
    const records = Array.isArray(historyPayload.records) ? historyPayload.records : [];
    const historyByDay = new Map();
    records.forEach(record => {
      const date = new Date(record.observed_at || record.timestamp);
      if (!Number.isNaN(date.getTime()) && hasNumber(record.temperature)) {
        historyByDay.set(date.toISOString().slice(0, 10), { date, temperature: Number(record.temperature) });
      }
    });
    const forecastItems = forecastPayload && forecastPayload.data && Array.isArray(forecastPayload.data.forecast)
      ? forecastPayload.data.forecast : [];
    const forecastByDay = new Map();
    forecastItems.forEach(item => {
      const date = parseForecastTime(item);
      if (!date || !hasNumber(item.temperature)) return;
      const key = date.toISOString().slice(0, 10);
      const entry = forecastByDay.get(key) || { date, values: [] };
      entry.values.push(Number(item.temperature));
      forecastByDay.set(key, entry);
    });

    const allDays = new Map();
    historyByDay.forEach((value, key) => allDays.set(key, { date: value.date, actual: value.temperature }));
    forecastByDay.forEach((value, key) => {
      const entry = allDays.get(key) || { date: value.date };
      entry.forecast = value.values.reduce((total, current) => total + current, 0) / value.values.length;
      allDays.set(key, entry);
    });
    const sorted = [...allDays.entries()].sort((a, b) => a[0].localeCompare(b[0])).slice(-14);
    const labels = sorted.map(([, item]) => dayLabel(item.date));
    const actualValues = sorted.map(([, item]) => Number.isFinite(item.actual) ? Number(item.actual.toFixed(1)) : null);
    const forecastValues = sorted.map(([, item]) => Number.isFinite(item.forecast) ? Number(item.forecast.toFixed(1)) : null);

    if (!sorted.length) {
      text('wiChartCaption', historyPayload.warning || 'No historical or forecast temperature observations are available.');
      return;
    }
    if (state.chart) state.chart.destroy();
    state.chart = new Chart($('wiTemperatureChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Historical',
            data: actualValues,
            borderColor: '#326cf4',
            backgroundColor: 'rgba(50,108,244,.10)',
            fill: true,
            tension: .35,
            pointRadius: 2.5,
            pointHoverRadius: 5,
            borderWidth: 2
          },
          {
            label: 'Forecast',
            data: forecastValues,
            borderColor: '#f0a94d',
            backgroundColor: 'rgba(240,169,77,.08)',
            fill: false,
            tension: .35,
            pointRadius: 2.5,
            pointHoverRadius: 5,
            borderWidth: 2,
            borderDash: [5, 4]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7, boxHeight: 7, padding: 17, color: '#758198', font: { family: 'DM Sans', size: 10 } } },
          tooltip: { backgroundColor: '#17233b', padding: 10, callbacks: { label: item => `${item.dataset.label}: ${item.parsed.y == null ? '—' : `${item.parsed.y}°C`}` } }
        },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { color: '#929caf', maxRotation: 0, autoSkip: true, maxTicksLimit: 7, font: { family: 'DM Sans', size: 9 } } },
          y: { border: { display: false, dash: [3, 3] }, grid: { color: '#eef1f6' }, ticks: { color: '#929caf', maxTicksLimit: 5, callback: value => `${value}°`, font: { family: 'DM Sans', size: 9 } } }
        }
      }
    });
    const source = historyPayload.source || 'historical archive';
    text('wiChartCaption', `${records.length} historical daily readings · ${forecastItems.length} forecast points · ${source}. Reanalysis is model-derived, not a station measurement.`);
  }

  function renderCyclones(data) {
    const cyclones = Array.isArray(data.cyclones) ? data.cyclones : [];
    text('wiCycloneSummary', data.status === 503 ? 'Feed unavailable' : String(cyclones.length));
    const container = $('wiCycloneDetails');
    state.cycloneMarkers.forEach(marker => state.cycloneMap && state.cycloneMap.removeLayer(marker));
    state.cycloneMarkers = [];
    const validCyclones = cyclones.filter(cyclone => hasNumber(cyclone.lat) && hasNumber(cyclone.lon));
    if (state.cycloneMap && validCyclones.length) {
      const points = [];
      validCyclones.forEach(cyclone => {
        const marker = L.marker([Number(cyclone.lat), Number(cyclone.lon)], {
          icon: L.divIcon({ className: '', html: '<span class="wi-storm-icon">✳</span>', iconSize: [30, 30], iconAnchor: [15, 15] })
        }).bindPopup(`<strong>${escapeHTML(cyclone.name || 'Active cyclone')}</strong><br>${escapeHTML(cyclone.category || cyclone.basin || 'Status under observation')}`);
        marker.addTo(state.cycloneMap);
        state.cycloneMarkers.push(marker);
        points.push([Number(cyclone.lat), Number(cyclone.lon)]);
      });
      if (points.length === 1) state.cycloneMap.setView(points[0], 4);
      else state.cycloneMap.fitBounds(points, { padding: [25, 25], maxZoom: 5 });
    } else if (state.weather && hasNumber(state.weather.lat) && hasNumber(state.weather.lon)) {
      state.cycloneMap.setView([Number(state.weather.lat), Number(state.weather.lon)], 3);
    }
    if (!container) return;
    if (data.status === 503) {
      container.textContent = data.message || 'Live cyclone feeds are unavailable; active conditions could not be confirmed.';
      return;
    }
    if (!cyclones.length) {
      container.textContent = data.message || 'No active cyclones reported by the available live sources.';
      return;
    }
    container.innerHTML = validCyclones.slice(0, 2).map(cyclone => `
      <div class="wi-cyclone-line"><span class="wi-storm-dot"></span><span><strong>${escapeHTML(cyclone.name || 'Active cyclone')}</strong><small>${escapeHTML([cyclone.category, cyclone.basin, hasNumber(cyclone.max_wind_speed) ? `${number(cyclone.max_wind_speed)} km/h winds` : ''].filter(Boolean).join(' · ') || 'Position reported by official feed')}</small></span></div>`).join('') || escapeHTML(data.message || 'Cyclone coordinates were not provided by the active feed.');
  }

  function addRadarLayer(frame) {
    if (!frame || !frame.path) return null;
    const template = `https://tilecache.rainviewer.com${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
    return L.tileLayer(template, { opacity: .58, attribution: '&copy; RainViewer', maxZoom: 12, zIndex: 350 });
  }

  async function loadMapOverlays() {
    state.overlayLayers.clouds = L.tileLayer(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_Cloud_Fraction_Day/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      {
        opacity: .58,
        maxZoom: 18,
        maxNativeZoom: 6,
        zIndex: 340,
        attribution: '&copy; NASA GIBS · MODIS Terra Cloud Fraction'
      }
    );
    try {
      const response = await fetch('https://api.rainviewer.com/public/weather-maps.json');
      if (!response.ok) throw new Error(`Overlay service returned ${response.status}`);
      const data = await response.json();
      const radarFrames = [...(data.radar && data.radar.past || []), ...(data.radar && data.radar.nowcast || [])];
      state.overlayLayers.radar = addRadarLayer(radarFrames[radarFrames.length - 1]);
    } catch (error) {
      text('wiMapStatus', `Radar overlay unavailable: ${error.message}`);
    }
  }

  function toggleOverlay(type, button) {
    const layer = state.overlayLayers[type];
    if (!layer) {
      text('wiMapStatus', `${type === 'clouds' ? 'Cloud cover' : 'Radar'} overlay is currently unavailable.`);
      button.setAttribute('aria-pressed', 'false');
      return;
    }
    if (state.activeOverlay === type) {
      state.mainMap.removeLayer(layer);
      state.activeOverlay = null;
      button.setAttribute('aria-pressed', 'false');
      text('wiMapStatus', 'Map overlay turned off. Map tiles © OpenStreetMap contributors.');
      return;
    }
    if (state.activeOverlay && state.overlayLayers[state.activeOverlay]) {
      state.mainMap.removeLayer(state.overlayLayers[state.activeOverlay]);
      const previousButton = $(state.activeOverlay === 'clouds' ? 'wiCloudToggle' : 'wiRadarToggle');
      if (previousButton) previousButton.setAttribute('aria-pressed', 'false');
    }
    layer.addTo(state.mainMap);
    state.activeOverlay = type;
    button.setAttribute('aria-pressed', 'true');
    text('wiMapStatus', type === 'clouds'
      ? 'Daily satellite cloud fraction · NASA GIBS / MODIS Terra'
      : 'Live radar overlay · RainViewer');
  }

  function initMaps() {
    if (typeof L === 'undefined') {
      text('wiMapStatus', 'Interactive maps are unavailable because the map library did not load.');
      return;
    }
    state.mainMap = L.map('wiMainMap', { zoomControl: false, scrollWheelZoom: false }).setView([22.5, 79], 4);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(state.mainMap);
    state.cycloneMap = L.map('wiCycloneMap', { zoomControl: false, scrollWheelZoom: false }).setView([20, 78], 3);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 12,
      attribution: '&copy; OpenStreetMap'
    }).addTo(state.cycloneMap);
    $('wiZoomIn').addEventListener('click', () => state.mainMap.zoomIn());
    $('wiZoomOut').addEventListener('click', () => state.mainMap.zoomOut());
    $('wiCloudToggle').addEventListener('click', event => toggleOverlay('clouds', event.currentTarget));
    $('wiRadarToggle').addEventListener('click', event => toggleOverlay('radar', event.currentTarget));
    window.setTimeout(() => {
      state.mainMap.invalidateSize();
      state.cycloneMap.invalidateSize();
    }, 250);
    loadMapOverlays();
  }

  async function loadDashboard(city = state.city) {
    state.city = city.trim() || state.city;
    const requestId = ++state.requestId;
    const queryCity = encodeURIComponent(state.city);
    const refresh = $('wiRefreshButton');
    if (refresh) refresh.classList.add('is-loading');
    state.weather = null;
    if (state.weatherMarker && state.mainMap) {
      state.mainMap.removeLayer(state.weatherMarker);
      state.weatherMarker = null;
    }
    text('wiCurrentCity', state.city);
    text('wiLocationSubtitle', `Loading live conditions and insights for ${state.city}.`);
    text('wiCurrentDate', 'Waiting for live conditions');
    text('wiTemperature', '--');
    text('wiCondition', 'Loading…');
    text('wiFeelsLike', 'Feels like --°');
    text('wiWind', '--');
    text('wiHumidity', '--');
    text('wiPressure', '--');
    text('wiSunTimes', '-- / --');
    text('wiWeatherSource', 'Weather data is loading');
    text('wiDailyRange', '--°  →  --°');
    text('wiPrecipitation', '--');
    text('wiCloudCover', '--');
    text('wiChartCaption', 'Loading archived observations and forecast data…');
    text('wiAlertSummary', '--');
    text('wiCycloneSummary', '--');
    $('wiAlertList').innerHTML = '<div class="wi-empty-state"><span class="wi-loading-ring"></span><span>Checking alert feed…</span></div>';
    text('wiCycloneDetails', 'Checking official cyclone feeds…');
    if (state.chart) {
      state.chart.destroy();
      state.chart = null;
    }
    const results = await Promise.allSettled([
      fetchJSON(`/weather/current?city=${queryCity}`),
      fetchJSON(`/weather/forecast?city=${queryCity}&days=5`),
      fetchJSON(`/weather/history?city=${queryCity}&days=7`),
      fetchJSON(`/alerts?city=${queryCity}`),
      fetchJSON('/cyclones/active')
    ]);

    if (requestId !== state.requestId) return;
    if (results[0].status === 'fulfilled') {
      try {
        const payload = results[0].value;
        renderWeather(payload.data || payload);
      } catch (error) {
        text('wiCondition', `Weather unavailable: ${error.message}`);
        $('wiWeatherSource').textContent = 'Current conditions could not be loaded.';
      }
    } else {
      text('wiCondition', `Weather unavailable: ${results[0].reason.message}`);
      text('wiWeatherSource', 'Current conditions could not be loaded from the API.');
    }

    if (results[1].status === 'rejected') text('wiChartCaption', `Forecast unavailable: ${results[1].reason.message}`);
    if (results[2].status === 'rejected') text('wiChartCaption', `Historical data unavailable: ${results[2].reason.message}`);
    if (results[1].status === 'fulfilled' && results[2].status === 'fulfilled') {
      try {
        renderTemperatureChart(results[2].value, results[1].value);
      } catch (error) {
        text('wiChartCaption', `Unable to render temperature trends: ${error.message}`);
      }
    }

    if (results[3].status === 'fulfilled') renderAlerts(results[3].value);
    else {
      text('wiAlertSummary', 'Unavailable');
      $('wiAlertList').innerHTML = `<div class="wi-empty-state is-error"><i class="bi bi-exclamation-circle"></i><span>Alert feed unavailable: ${escapeHTML(results[3].reason.message)}</span></div>`;
    }
    if (results[4].status === 'fulfilled') renderCyclones(results[4].value);
    else {
      text('wiCycloneSummary', 'Unavailable');
      text('wiCycloneDetails', `Cyclone feed unavailable: ${results[4].reason.message}`);
    }

    text('wiUpdated', `Updated ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date())}`);
    text('wiFooterSource', 'Weather: Open-Meteo · Map: OpenStreetMap · Alerts & cyclone status: live feeds');
    if (refresh && requestId === state.requestId) refresh.classList.remove('is-loading');
  }

  function setupInteractions() {
    $('wiSearchForm').addEventListener('submit', event => {
      event.preventDefault();
      const city = $('wiCitySearch').value.trim();
      if (!city) return;
      localStorage.setItem('weatheriq_last_city', city);
      loadDashboard(city);
      $('wiCitySearch').blur();
    });
    $('wiRefreshButton').addEventListener('click', () => loadDashboard());
    $('wiNotificationButton').addEventListener('click', () => { window.location.href = 'pages/alerts.html'; });
    window.addEventListener('resize', () => {
      if (state.mainMap) state.mainMap.invalidateSize();
      if (state.cycloneMap) state.cycloneMap.invalidateSize();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupInteractions();
    initMaps();
    loadDashboard();
  });
})();
