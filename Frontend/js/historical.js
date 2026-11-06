/**
 * WeatherIQ - Historical Telemetry & Cyclone Archive Controller
 */

async function loadHistoricalData(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const subtitle = document.getElementById('histSubtitle');
  const daysSelect = document.getElementById('histDaysSelect');
  const days = daysSelect ? daysSelect.value : 30;

  if (subtitle) subtitle.textContent = `Persisted weather observations for ${city} (Past ${days} days)`;

  const tbody = document.getElementById('historicalTableBody');
  const badge = document.getElementById('recordCountBadge');
  const warning = document.getElementById('historyWarning');

  try {
    const res = await window.weatherApp.fetchAPI(`/weather/history?city=${encodeURIComponent(city)}&days=${days}`);
    const records = res.records || [];

    if (warning) {
      warning.hidden = !res.warning;
      warning.textContent = res.warning ? `Archive update unavailable; showing saved verified readings. ${res.warning}` : '';
    }
    if (badge) badge.textContent = `${records.length} Records`;

    if (!records.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center py-4 text-muted">
            No verified historical weather records are available for '${city}' in this date range.
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = records.map(r => `
        <tr>
          <td>${window.weatherApp.formatDateTime(r.observed_at)}</td>
          <td><strong>${escapeHistoricalText(r.city || city)}</strong></td>
          <td>${window.weatherApp.getWeatherIcon(r.weather_icon)} ${escapeHistoricalText(r.weather_description || r.weather_main || '--')}</td>
          <td>${window.weatherApp.formatTemperature(r.temperature)}</td>
          <td>${r.humidity ?? '--'}%</td>
          <td>${r.pressure ?? '--'} hPa</td>
          <td>${window.weatherApp.formatWindSpeed(r.wind_speed)}</td>
          <td>${escapeHistoricalText(r.source || 'Legacy (unverified)')}</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.warn('Historical data error:', err);
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-3 text-danger">Error: ${err.message}</td></tr>`;
    }
  }

  loadHistoricalCyclones();
}

function escapeHistoricalText(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

async function loadHistoricalCyclones() {
  const container = document.getElementById('historicalCyclonesList');
  if (!container) return;

  try {
    const res = await window.weatherApp.fetchAPI('/cyclones/historical');
    const list = res.data && Array.isArray(res.data.cyclones) ? res.data.cyclones : [];

    if (!list.length) {
      container.innerHTML = '<div class="col-12 text-muted">No historical cyclone records are stored in the database yet.</div>';
      return;
    }

    container.innerHTML = list.map(c => `
      <div class="col-md-6 col-lg-4">
        <div class="historical-cyclone-card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="color:#b91c1c; font-size:15px;">🌀 ${c.name}</strong>
            <span class="badge bg-secondary">${c.year || 'Historical'}</span>
          </div>
          <div style="font-size:12px; color:var(--color-text-primary); margin-bottom:4px;">${c.category}</div>
          <div style="font-size:12px; color:var(--color-text-muted); line-height:1.6;">
            <div>Peak Wind: ${c.wind || (c.max_wind_speed ? c.max_wind_speed + ' km/h' : '--')}</div>
            <div>Basin: ${c.basin || 'NIO'}</div>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.warn('Historical cyclones catalog notice:', err);
  }
}

window.reloadCurrentPageData = function(city) {
  loadHistoricalData(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadHistoricalData();

  const daysSelect = document.getElementById('histDaysSelect');
  if (daysSelect) {
    daysSelect.addEventListener('change', () => loadHistoricalData());
  }
});
