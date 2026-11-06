/**
 * WeatherIQ - Disaster Risk Assessment Controller
 */

async function loadRiskAssessment(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const header = document.getElementById('riskCityHeader');
  if (header) header.textContent = `Vulnerability and environmental hazard assessment for ${city}`;

  const scoreEl = document.getElementById('riskScore');
  const badgeEl = document.getElementById('riskLevelBadge');
  const windVal = document.getElementById('windRiskVal');
  const windBar = document.getElementById('windRiskBar');
  const rainVal = document.getElementById('rainRiskVal');
  const rainBar = document.getElementById('rainRiskBar');
  const floodVal = document.getElementById('floodRiskVal');
  const floodBar = document.getElementById('floodRiskBar');
  const surgeVal = document.getElementById('surgeRiskVal');
  const surgeBar = document.getElementById('surgeRiskBar');
  const recsContainer = document.getElementById('recommendationsList');
  const factorsContainer = document.getElementById('contributingFactorsList');

  try {
    const res = await window.weatherApp.fetchAPI(`/risk/assessment?city=${encodeURIComponent(city)}`);
    const data = res.data || {};

    const overall = data.overall_score ?? '--';
    const level = data.risk_level || 'Unavailable';

    if (scoreEl) scoreEl.textContent = overall;
    if (badgeEl) {
      badgeEl.textContent = `${level.toUpperCase()} HAZARD LEVEL`;
      badgeEl.className = 'badge';
      if (level === 'Low') badgeEl.style.background = 'var(--color-success)';
      else if (level === 'Moderate') badgeEl.style.background = 'var(--color-warning)';
      else if (level === 'High') badgeEl.style.background = '#ea580c';
      else if (level === 'Unavailable') badgeEl.style.background = 'var(--color-text-muted)';
      else badgeEl.style.background = 'var(--color-danger)';
    }

    const ind = data.individual_risks || {};
    const setRiskMetric = (value, label, bar) => {
      const score = value == null || !Number.isFinite(Number(value))
        ? null
        : Math.max(0, Math.min(100, Number(value)));
      if (label) label.textContent = score == null ? 'Unavailable' : `${score} / 100`;
      if (bar) bar.style.width = `${score ?? 0}%`;
    };

    setRiskMetric(ind.wind_risk, windVal, windBar);
    setRiskMetric(ind.rainfall_risk, rainVal, rainBar);
    setRiskMetric(ind.flood_risk, floodVal, floodBar);
    setRiskMetric(ind.storm_surge_risk, surgeVal, surgeBar);

    // Recommendations
    if (recsContainer) {
      const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
      recsContainer.replaceChildren();
      if (recommendations.length) {
        const list = document.createElement('ul');
        list.className = 'risk-text-list';
        recommendations.forEach(item => {
          const entry = document.createElement('li');
          entry.textContent = item;
          list.appendChild(entry);
        });
        recsContainer.appendChild(list);
      } else {
        recsContainer.textContent = 'Recommendations are unavailable for the current assessment.';
      }
    }

    // Factors
    if (factorsContainer) {
      const factors = Array.isArray(data.contributing_factors) ? data.contributing_factors : [];
      factorsContainer.replaceChildren();
      if (factors.length) {
        factors.forEach(factor => {
          const entry = document.createElement('div');
          entry.className = 'risk-factor';
          entry.textContent = `• ${factor}`;
          factorsContainer.appendChild(entry);
        });
      } else {
        factorsContainer.textContent = 'Contributing factors are unavailable for the current assessment.';
      }
    }
  } catch (err) {
    console.warn('Risk assessment error:', err);
    if (scoreEl) scoreEl.textContent = '--';
    if (badgeEl) {
      badgeEl.textContent = 'ASSESSMENT UNAVAILABLE';
      badgeEl.style.background = 'var(--color-text-muted)';
    }
    [windVal, rainVal, floodVal, surgeVal].forEach(element => {
      if (element) element.textContent = 'Unavailable';
    });
    [windBar, rainBar, floodBar, surgeBar].forEach(element => {
      if (element) element.style.width = '0%';
    });
    if (recsContainer) recsContainer.textContent = `Recommendations unavailable: ${err.message}`;
    if (factorsContainer) factorsContainer.textContent = `Risk factors unavailable: ${err.message}`;
  }
}

window.reloadCurrentPageData = function(city) {
  loadRiskAssessment(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadRiskAssessment();

  const runBtn = document.getElementById('runRiskAssessmentBtn');
  const input = document.getElementById('riskCityInput');
  if (runBtn && input) {
    runBtn.addEventListener('click', () => {
      const city = input.value.trim();
      if (city) {
        window.weatherApp.handleCitySearch(city);
        loadRiskAssessment(city);
      }
    });
  }
});
