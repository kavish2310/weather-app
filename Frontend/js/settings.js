/**
 * WeatherIQ - Settings & Configuration Controller
 */

async function loadSettings() {
  loadDisplayPreferences();
  checkApiStatus();
  loadFavoritesManager();
}

function loadDisplayPreferences() {
  const prefs = window.weatherApp.preferences;
  const tempSelect = document.getElementById('prefTempUnit');
  const windSelect = document.getElementById('prefWindUnit');
  const timeSelect = document.getElementById('prefTimeFormat');
  const refreshSelect = document.getElementById('prefRefreshRate');

  if (tempSelect) tempSelect.value = prefs.tempUnit || 'celsius';
  if (windSelect) windSelect.value = prefs.windUnit || 'kmh';
  if (timeSelect) timeSelect.value = prefs.timeFormat || '24h';
  if (refreshSelect) refreshSelect.value = String(prefs.refreshRate || 15);
}

async function checkApiStatus() {
  const owmBadge = document.getElementById('owmKeyStatus');
  try {
    const configRes = await window.weatherApp.fetchAPI('/settings/config');
    if (owmBadge) {
      if (configRes.api_configured) {
        owmBadge.className = 'badge bg-success';
        owmBadge.textContent = 'Configured & Active';
      } else {
        owmBadge.className = 'badge bg-warning';
        owmBadge.textContent = 'Not Set in .env (Add OPENWEATHERMAP_API_KEY)';
      }
    }
  } catch (e) {
    if (owmBadge) {
      owmBadge.className = 'badge bg-danger';
      owmBadge.textContent = 'Connection Error';
    }
  }
}

async function loadFavoritesManager() {
  const container = document.getElementById('favoritesListGroup');
  if (!container) return;

  try {
    const res = await window.weatherApp.fetchAPI('/settings/favorites');
    const favs = res.favorites || [];

    if (!favs.length) {
      container.innerHTML = '<div class="text-muted" style="font-size:13px;">No favorites added yet. Add your favorite cities above.</div>';
      return;
    }

    container.innerHTML = favs.map(f => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:13px; font-weight:500;">⭐ ${f.name} ${f.country ? '(' + f.country + ')' : ''}</span>
        <button class="btn btn-sm btn-outline-danger" onclick="deleteFavorite(${f.id})" style="font-size:11px; padding:2px 8px;">Remove</button>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = '<div class="text-danger" style="font-size:13px;">Failed to load favorites</div>';
  }
}

async function deleteFavorite(cityId) {
  try {
    await window.weatherApp.fetchAPI(`/settings/favorites/${cityId}`, { method: 'DELETE' });
    window.weatherApp.showToast('City removed from favorites.', 'info');
    loadFavoritesManager();
  } catch (err) {
    window.weatherApp.showToast('Failed to remove favorite.', 'danger');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadSettings();

  const saveBtn = document.getElementById('savePrefsBtn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const tempUnit = document.getElementById('prefTempUnit').value;
      const windUnit = document.getElementById('prefWindUnit').value;
      const timeFormat = document.getElementById('prefTimeFormat').value;
      const refreshRate = parseInt(document.getElementById('prefRefreshRate').value, 10);

      window.weatherApp.savePreferences({ tempUnit, windUnit, timeFormat, refreshRate });
      window.weatherApp.setupAutoRefresh();
      window.weatherApp.showToast('Telemetry preferences saved successfully!', 'success');
    });
  }

  const checkBtn = document.getElementById('checkApiBtn');
  if (checkBtn) {
    checkBtn.addEventListener('click', () => {
      window.weatherApp.showToast('Probing backend API and meteorological gateways...', 'info');
      checkApiStatus();
    });
  }

  const addFavBtn = document.getElementById('addFavoriteBtn');
  const favInput = document.getElementById('newFavoriteInput');
  if (addFavBtn && favInput) {
    addFavBtn.addEventListener('click', async () => {
      const val = favInput.value.trim();
      if (!val) return;
      try {
        await window.weatherApp.fetchAPI('/settings/favorites', {
          method: 'POST',
          body: JSON.stringify({ city: val })
        });
        favInput.value = '';
        window.weatherApp.showToast(`'${val}' added to favorites!`, 'success');
        loadFavoritesManager();
      } catch (e) {
        window.weatherApp.showToast(`Error adding favorite: ${e.message}`, 'danger');
      }
    });
  }

  const clearHistoryBtn = document.getElementById('clearSearchHistoryBtn');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', async () => {
      try {
        await window.weatherApp.fetchAPI('/settings/search-history', { method: 'DELETE' });
      } catch (e) {}
      localStorage.removeItem('weatheriq_recent');
      window.weatherApp.showToast('Search history cleared.', 'success');
    });
  }

  const clearCacheBtn = document.getElementById('clearAppCacheBtn');
  if (clearCacheBtn) {
    clearCacheBtn.addEventListener('click', () => {
      localStorage.clear();
      window.weatherApp.showToast('Application local storage cleared. Reloading...', 'warning');
      setTimeout(() => window.location.reload(), 1000);
    });
  }
});
