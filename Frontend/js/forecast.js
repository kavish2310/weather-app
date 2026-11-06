/**
 * WeatherIQ - Machine Learning Forecasting & Anomaly Detection Controller
 */

let activeModel = 'temperature';

async function loadForecastPage(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const header = document.getElementById('mlCityHeader');
  if (header) header.textContent = `Model evaluation & predictive inference for ${city}`;

  const notice = document.getElementById('mlDataNotice');
  const msg = document.getElementById('mlNoticeMessage');
  const maeEl = document.getElementById('metricMAE');
  const rmseEl = document.getElementById('metricRMSE');
  const r2El = document.getElementById('metricR2');

  try {
    const res = await window.weatherApp.fetchAPI(`/analytics/predictions?city=${encodeURIComponent(city)}&model=${activeModel}`);

    if (res.sufficient_data === false || res.status === 'insufficient_data') {
      if (notice) {
        notice.style.display = 'block';
        notice.className = 'alert alert-warning mb-4';
      }
      if (msg) {
        msg.textContent = res.archive_notice
          ? `${res.message || 'Insufficient verified history for local model training.'} ${res.archive_notice}`
          : res.message || 'Insufficient verified historical data for reliable local ML training. A live, archive-backed forecast is shown as an operational baseline while more data is collected.';
      }

      if (maeEl) maeEl.textContent = 'Pending';
      if (rmseEl) rmseEl.textContent = 'Pending';
      if (r2El) r2El.textContent = 'Pending';

      // Load NWP forecast as visual baseline
      loadForecastFallback(city);
      return;
    }

    // When sufficient data exists
    if (notice) {
      notice.style.display = 'block';
      notice.className = 'alert alert-success mb-4';
      notice.style.background = '#ecfdf5';
      notice.style.borderColor = '#10b981';
      notice.style.color = '#065f46';
    }
    if (msg) {
      const sourceNames = (res.training_data_sources || []).map(source =>
        source.includes('reanalysis') ? 'Open-Meteo historical reanalysis' : 'Open-Meteo live model data'
      );
      const sourceText = [...new Set(sourceNames)].join(' and ') || 'verified Open-Meteo data';
      const sampleCount = Number.isFinite(res.training_observations)
        ? `${res.training_observations} archived weather-model readings`
        : 'verified Open-Meteo readings';
      msg.textContent = `Trained on ${sampleCount} from ${sourceText}; validated on a chronological test set. Historical reanalysis is model-derived, not a station measurement. Model type: ${res.metrics ? res.metrics.model_type : 'Ridge Regression'}.`;
    }

    if (res.metrics) {
      if (maeEl) maeEl.textContent = `${res.metrics.mae} °C`;
      if (rmseEl) rmseEl.textContent = `${res.metrics.rmse} °C`;
      if (r2El) r2El.textContent = res.metrics.r2;
    }

    if (res.predictions && res.predictions.length) {
      const labels = res.predictions.map(p => `+${p.hour_offset}h`);
      const temps = res.predictions.map(p => p.predicted_temperature);
      window.weatherCharts.renderTrend('mlForecastChart', 'ML Predicted Temperature (°C)', labels, temps, 'cyan');
    }
  } catch (err) {
    console.warn('ML predictions notice:', err);
    loadForecastFallback(city);
  }
}

async function loadForecastFallback(city) {
  try {
    const fRes = await window.weatherApp.fetchAPI(`/weather/forecast?city=${encodeURIComponent(city)}&days=5`);
    const items = (fRes.data && fRes.data.forecast) ? fRes.data.forecast.slice(0, 10) : [];
    if (items.length) {
      const labels = items.map(i => {
        const d = new Date(i.dt_txt);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      });
      const temps = items.map(i => i.temperature);
      window.weatherCharts.renderTrend('mlForecastChart', 'NWP Physics Baseline (°C)', labels, temps, 'amber');
    }
  } catch (e) {
    console.warn('Fallback chart error:', e);
  }
}

window.reloadCurrentPageData = function(city) {
  loadForecastPage(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadForecastPage();

  const modelButtons = document.querySelectorAll('.ml-model-btn');
  modelButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      modelButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeModel = btn.getAttribute('data-model');
      loadForecastPage();
    });
  });
});
