/**
 * WeatherIQ - Core Application Utilities & State Management
 */

// If opened from file://, default to http://127.0.0.1:5000/api
const API_BASE_URL = (typeof window !== 'undefined' && (window.location.protocol === 'file:' || !window.location.origin || window.location.origin === 'null'))
  ? 'http://127.0.0.1:5000/api'
  : (window.location.origin + '/api');

class WeatherApp {
  constructor() {
    this.currentCity = localStorage.getItem('weatheriq_last_city') || 'Indore';
    this.preferences = this.loadPreferences();
    this.refreshInterval = null;
  }

  init() {
    this.setupNavbar();
    this.setupSearch();
    this.setupTheme();
    this.setupAutoRefresh();
    this.updateNotificationBadge();
  }

  loadPreferences() {
    const defaultPrefs = {
      tempUnit: 'celsius',
      windUnit: 'kmh',
      timeFormat: '24h',
      refreshRate: 15
    };
    const stored = localStorage.getItem('weatheriq_prefs');
    return stored ? { ...defaultPrefs, ...JSON.parse(stored) } : defaultPrefs;
  }

  savePreferences(prefs) {
    this.preferences = { ...this.preferences, ...prefs };
    localStorage.setItem('weatheriq_prefs', JSON.stringify(this.preferences));
  }

  setupNavbar() {
    const hamburgerBtn = document.getElementById('hamburgerBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (hamburgerBtn && sidebar) {
      hamburgerBtn.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
      });
    }

    if (overlay && sidebar) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
      });
    }

    const locBtn = document.getElementById('locationBtn');
    if (locBtn) {
      locBtn.addEventListener('click', () => this.useCurrentLocation());
    }

    const notifBtn = document.getElementById('notificationBtn');
    if (notifBtn) {
      notifBtn.addEventListener('click', () => {
        const inPages = window.location.pathname.includes('/pages/');
        window.location.href = inPages ? 'alerts.html' : 'pages/alerts.html';
      });
    }
  }

  setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const val = searchInput.value.trim();
        if (val) {
          this.handleCitySearch(val);
        }
      }
    });
  }

  setupTheme() {
    const themeToggle = document.getElementById('themeToggle');
    const applyTheme = (theme) => {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem('weatheriq_theme', theme);
      if (themeToggle) {
        const nextTheme = theme === 'light' ? 'dark' : 'light';
        const label = `Switch to ${nextTheme} theme`;
        themeToggle.textContent = theme === 'light' ? '🌙' : '☀️';
        themeToggle.title = label;
        themeToggle.setAttribute('aria-label', label);
      }
      window.dispatchEvent(new CustomEvent('weatheriq:themechange', { detail: { theme } }));
    };

    applyTheme(localStorage.getItem('weatheriq_theme') || 'light');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const nextTheme = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
        applyTheme(nextTheme);
      });
    }
  }

  setupAutoRefresh() {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
    const ms = (this.preferences.refreshRate || 15) * 60 * 1000;
    this.refreshInterval = setInterval(() => {
      if (typeof window.reloadCurrentPageData === 'function') {
        window.reloadCurrentPageData();
      }
    }, ms);
  }

  handleCitySearch(city) {
    this.currentCity = city;
    localStorage.setItem('weatheriq_last_city', city);
    this.addRecentCity(city);

    if (typeof window.reloadCurrentPageData === 'function') {
      window.reloadCurrentPageData(city);
    } else {
      window.location.reload();
    }
  }

  useCurrentLocation() {
    if (!navigator.geolocation) {
      this.showToast('Geolocation is not supported by your browser.', 'warning');
      return;
    }

    this.showToast('Locating coordinates...', 'info');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        try {
          const res = await this.fetchAPI(`/weather/current?lat=${latitude}&lon=${longitude}`);
          if (res && res.data && res.data.city) {
            this.handleCitySearch(res.data.city);
            this.showToast(`Located: ${res.data.city}, ${res.data.country}`, 'success');
          }
        } catch (err) {
          this.showToast('Failed to retrieve weather for location.', 'danger');
        }
      },
      (err) => {
        this.showToast(`Location error: ${err.message}`, 'danger');
      }
    );
  }

  async fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const res = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || `HTTP error ${res.status}`);
      }
      return data;
    } catch (err) {
      console.warn(`API call (${endpoint}) note:`, err.message);
      throw err;
    }
  }

  formatTemperature(celsius) {
    if (celsius === null || celsius === undefined || isNaN(celsius)) return '--';
    if (this.preferences.tempUnit === 'fahrenheit') {
      const f = (celsius * 9) / 5 + 32;
      return `${Math.round(f)}°F`;
    }
    return `${Math.round(celsius)}°C`;
  }

  formatWindSpeed(speedMs) {
    if (speedMs === null || speedMs === undefined || isNaN(speedMs)) return '--';
    if (this.preferences.windUnit === 'ms') {
      return `${Number(speedMs).toFixed(1)} m/s`;
    } else if (this.preferences.windUnit === 'mph') {
      return `${(Number(speedMs) * 2.23694).toFixed(1)} mph`;
    }
    return `${(Number(speedMs) * 3.6).toFixed(1)} km/h`;
  }

  formatDateTime(isoStr) {
    if (!isoStr) return '--';
    try {
      const dt = new Date(isoStr);
      return dt.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: this.preferences.timeFormat === '12h'
      });
    } catch {
      return isoStr;
    }
  }

  getWeatherIcon(code) {
    const map = {
      '01d': '☀️', '01n': '🌙',
      '02d': '⛅', '02n': '☁️',
      '03d': '☁️', '03n': '☁️',
      '04d': '☁️', '04n': '☁️',
      '09d': '🌧️', '09n': '🌧️',
      '10d': '🌦️', '10n': '🌧️',
      '11d': '⛈️', '11n': '⛈️',
      '13d': '❄️', '13n': '❄️',
      '50d': '🌫️', '50n': '🌫️'
    };
    return map[code] || '🌤️';
  }

  addRecentCity(city) {
    let recent = JSON.parse(localStorage.getItem('weatheriq_recent') || '[]');
    recent = recent.filter(c => c.toLowerCase() !== city.toLowerCase());
    recent.unshift(city);
    if (recent.length > 5) recent.pop();
    localStorage.setItem('weatheriq_recent', JSON.stringify(recent));
  }

  getRecentCities() {
    return JSON.parse(localStorage.getItem('weatheriq_recent') || '["Indore", "Mumbai", "Delhi", "Pune"]');
  }

  async updateNotificationBadge() {
    try {
      const badge = document.getElementById('notifBadge');
      if (!badge) return;
      const res = await this.fetchAPI('/alerts');
      const count = res.count || (res.alerts ? res.alerts.length : 0);
      if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
    } catch (e) {
      // Non-blocking
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type} animate-slide-up`;
    toast.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
        <span>${message}</span>
        <button style="background:none; border:none; color:inherit; cursor:pointer;" onclick="this.parentElement.parentElement.remove()">✕</button>
      </div>
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4500);
  }
}

// Global App Instance
window.weatherApp = new WeatherApp();
document.addEventListener('DOMContentLoaded', () => {
  window.weatherApp.init();
});
