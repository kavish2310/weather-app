/**
 * WeatherIQ - Weather Analytics Controller
 */

let currentPeriod = '24h';

const analyticsCharts = [
  'tempTrendChart',
  'humidityTrendChart',
  'pressureTrendChart',
  'windTrendChart'
];

function formatAnalyticsTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';

  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function makeSeries(points, source, field, convert = value => value) {
  return points.map(point => {
    if (point.source !== source || point[field] === null || point[field] === undefined) {
      return null;
    }
    const value = Number(point[field]);
    return Number.isFinite(value) ? convert(value) : null;
  });
}

function makeDataset(label, data, color, forecast = false, yAxisID = 'y') {
  return {
    label,
    data,
    borderColor: color,
    backgroundColor: `${color}22`,
    borderDash: forecast ? [6, 4] : [],
    fill: false,
    tension: 0.3,
    pointRadius: 2,
    pointHoverRadius: 5,
    spanGaps: false,
    yAxisID
  };
}

function renderAnalyticsTimeSeries(result) {
  const observations = (result.observations || []).map(point => ({ ...point, source: 'observed' }));
  const forecasts = (result.forecasts || []).map(point => ({ ...point, source: 'forecast' }));
  const points = observations.concat(forecasts)
    .filter(point => point.timestamp && !Number.isNaN(new Date(point.timestamp).getTime()))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const labels = points.map(point => formatAnalyticsTimestamp(point.timestamp));
  const observed = 'observed';
  const predicted = 'forecast';
  const colors = {
    observed: { temperature: '#06b6d4', feels: '#8b5cf6', humidity: '#60a5fa', pressure: '#f59e0b', wind: '#10b981', direction: '#f97316' },
    forecast: { temperature: '#06b6d4', feels: '#8b5cf6', humidity: '#60a5fa', pressure: '#f59e0b', wind: '#10b981', direction: '#f97316' },
  };

  window.weatherCharts.renderTimeSeries('tempTrendChart', labels, [
    makeDataset('Observed temperature (°C)', makeSeries(points, observed, 'temperature'), colors.observed.temperature),
    makeDataset('Observed feels like (°C)', makeSeries(points, observed, 'feels_like'), colors.observed.feels),
    makeDataset('Forecast temperature (°C)', makeSeries(points, predicted, 'temperature'), colors.forecast.temperature, true),
    makeDataset('Forecast feels like (°C)', makeSeries(points, predicted, 'feels_like'), colors.forecast.feels, true)
  ], 'Temperature (°C)');

  window.weatherCharts.renderTimeSeries('humidityTrendChart', labels, [
    makeDataset('Observed humidity (%)', makeSeries(points, observed, 'humidity'), colors.observed.humidity),
    makeDataset('Forecast humidity (%)', makeSeries(points, predicted, 'humidity'), colors.forecast.humidity, true)
  ], 'Relative humidity (%)', { min: 0, max: 100 });

  window.weatherCharts.renderTimeSeries('pressureTrendChart', labels, [
    makeDataset('Observed pressure (hPa)', makeSeries(points, observed, 'pressure'), colors.observed.pressure),
    makeDataset('Forecast pressure (hPa)', makeSeries(points, predicted, 'pressure'), colors.forecast.pressure, true)
  ], 'Pressure (hPa)');

  window.weatherCharts.renderTimeSeries('windTrendChart', labels, [
    makeDataset('Observed wind speed (km/h)', makeSeries(points, observed, 'wind_speed', speed => speed * 3.6), colors.observed.wind),
    makeDataset('Forecast wind speed (km/h)', makeSeries(points, predicted, 'wind_speed', speed => speed * 3.6), colors.forecast.wind, true),
    makeDataset('Observed wind direction (°)', makeSeries(points, observed, 'wind_deg'), colors.observed.direction, false, 'y1'),
    makeDataset('Forecast wind direction (°)', makeSeries(points, predicted, 'wind_deg'), colors.forecast.direction, true, 'y1')
  ], 'Wind speed (km/h)', { title: 'Wind direction (°)', min: 0, max: 360 });

  return { observationCount: observations.length, forecastCount: forecasts.length };
}

function setAnalyticsStatus(message, kind = 'info') {
  const status = document.getElementById('analyticsStatus');
  if (!status) return;
  status.textContent = message;
  status.className = `analytics-status analytics-status-${kind}`;
}

async function loadAnalytics(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const subtitle = document.getElementById('analyticsSubtitle');
  if (subtitle) subtitle.textContent = `Observed weather and forecast trends for ${city} (${currentPeriod})`;
  setAnalyticsStatus('Loading weather data…');

  try {
    const result = await window.weatherApp.fetchAPI(
      `/analytics/timeseries?city=${encodeURIComponent(city)}&period=${currentPeriod}`
    );
    const counts = renderAnalyticsTimeSeries(result);

    if (!counts.observationCount && !counts.forecastCount) {
      setAnalyticsStatus(
        `No saved observations or forecasts for ${result.city}. Open Live Weather to fetch and save data for this city.`,
        'warning'
      );
    } else {
      setAnalyticsStatus(
        `${counts.observationCount} saved observations and ${counts.forecastCount} forecast points loaded for ${result.city}. Forecast lines are dashed.`,
        'success'
      );
    }
  } catch (error) {
    console.error('Analytics time-series error:', error);
    analyticsCharts.forEach(chartId => window.weatherCharts.renderTimeSeries(chartId, [], [], ''));
    setAnalyticsStatus(`Could not load chart data: ${error.message}`, 'error');
  }

  try {
    const response = await window.weatherApp.fetchAPI(
      '/weather/multiple?cities=Indore,Mumbai,Delhi,Pune,Chennai'
    );
    const cities = response.data && response.data.cities ? response.data.cities : [];
    if (cities.length) {
      window.weatherCharts.renderComparison('multiCityChart', cities.map(item => item.city), [
        {
          label: 'Temperature (°C)',
          data: cities.map(item => Number(item.temperature)),
          backgroundColor: '#06b6d4',
          yAxisID: 'y'
        },
        {
          label: 'Humidity (%)',
          data: cities.map(item => Number(item.humidity)),
          backgroundColor: '#3b82f6',
          yAxisID: 'y1'
        }
      ]);
    } else {
      window.weatherCharts.renderComparison('multiCityChart', [], []);
    }
  } catch (error) {
    console.error('City comparison error:', error);
    window.weatherCharts.renderComparison('multiCityChart', [], []);
  }
}

window.reloadCurrentPageData = function(city) {
  loadAnalytics(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadAnalytics();

  const buttons = document.querySelectorAll('.period-btn');
  buttons.forEach(button => {
    button.addEventListener('click', () => {
      buttons.forEach(item => item.classList.remove('active'));
      button.classList.add('active');
      currentPeriod = button.getAttribute('data-period');
      loadAnalytics();
    });
  });
});
