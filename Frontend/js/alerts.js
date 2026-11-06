/**
 * WeatherIQ - Alerts & Early Warning Center Controller
 */

let allAlertsList = [];

function escapeAlertText(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[character]);
}

async function loadAlerts() {
  const container = document.getElementById('alertsFeedContainer');
  const countBadge = document.getElementById('alertsCount');
  const filterVal = document.getElementById('alertSeverityFilter') ? document.getElementById('alertSeverityFilter').value : 'all';

  try {
    const res = await window.weatherApp.fetchAPI('/alerts');
    const alerts = res.alerts || [];
    allAlertsList = alerts;

    // Filter
    let filtered = alerts;
    if (filterVal !== 'all') {
      filtered = alerts.filter(a => (a.severity || '').toLowerCase() === filterVal);
    }

    if (countBadge) countBadge.textContent = `${filtered.length} Active`;

    if (!filtered.length) {
      container.innerHTML = `
        <div class="empty-state" style="padding:40px;">
          <div class="empty-state-icon">✅</div>
          <div class="empty-state-title" style="color:#047857;">No active weather alerts</div>
          <div class="empty-state-desc">No alerts are currently recorded for this filter. This does not replace official local warnings.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(a => {
      const isCrit = (a.severity || '').toLowerCase() === 'critical';
      const isWarn = (a.severity || '').toLowerCase() === 'warning';
      const badgeClass = isCrit ? 'bg-danger' : isWarn ? 'bg-warning' : 'bg-info';
      const icon = a.alert_type === 'heavy_rainfall' ? '🌧️' : a.alert_type === 'extreme_temperature' ? '☀️' : '💨';
      const severityClass = isCrit ? 'critical' : isWarn ? 'warning' : 'info';
      const issuedAt = window.weatherApp.formatDateTime(a.created_at || a.issued_at);
      const alertId = Number(a.id);

      return `
        <article class="weather-alert-card severity-${severityClass}">
          <div class="weather-alert-heading">
            <div class="weather-alert-title-group">
              <span style="font-size:22px;">${icon}</span>
              <div>
                <h2 class="weather-alert-title">${escapeAlertText(a.title || 'Weather alert')}</h2>
                <div class="weather-alert-meta">Issued by: ${escapeAlertText(a.issuing_authority || 'Meteorological Centre')} &middot; ${escapeAlertText(issuedAt)}</div>
              </div>
            </div>
            <span class="badge ${badgeClass} weather-alert-badge">${escapeAlertText(a.severity || 'info')}</span>
          </div>

          <p class="weather-alert-description">${escapeAlertText(a.description || 'No description provided.')}</p>

          <div class="weather-alert-action">
            <strong>Recommended safety measure</strong>
            <div>${escapeAlertText(a.recommended_action || 'Monitor official updates.')}</div>
          </div>

          <div class="weather-alert-footer">
            <span>Zone: <strong>${escapeAlertText(a.affected_area || 'Regional')}</strong></span>
            ${!a.is_read && Number.isInteger(alertId) ? `<button class="btn btn-sm btn-outline-secondary" onclick="markAlertRead(${alertId})">Acknowledge</button>` : '<span class="weather-alert-acknowledged">✓ Acknowledged</span>'}
          </div>
        </article>
      `;
    }).join('');
  } catch (err) {
    console.warn('Alerts loading notice:', err);
    if (container) {
      container.innerHTML = `<div class="alert-error" role="alert">Weather alerts could not be loaded: ${escapeAlertText(err.message)}</div>`;
    }
    if (countBadge) countBadge.textContent = 'Unavailable';
  }
}

async function markAlertRead(alertId) {
  try {
    await window.weatherApp.fetchAPI(`/alerts/read/${alertId}`, { method: 'POST' });
    window.weatherApp.showToast('Alert acknowledged.', 'success');
  } catch (error) {
    window.weatherApp.showToast(`Could not acknowledge alert: ${error.message}`, 'danger');
    return;
  }
  const item = allAlertsList.find(a => a.id === alertId);
  if (item) item.is_read = true;
  loadAlerts();
}

document.addEventListener('DOMContentLoaded', () => {
  loadAlerts();

  const filter = document.getElementById('alertSeverityFilter');
  if (filter) {
    filter.addEventListener('change', () => loadAlerts());
  }
});
