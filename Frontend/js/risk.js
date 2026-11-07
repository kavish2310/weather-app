/**
 * WeatherIQ - Disaster Risk Assessment Controller
 */

let riskRequestId = 0;
let cycloneFeedRequestId = 0;
let activeRiskCyclones = [];
let visibleRiskCyclones = [];
let riskCycloneMapReady = false;
let riskCycloneCheckedAt = null;
let cycloneForecastRequestId = 0;
let cycloneEnvironmentRequestId = 0;
let cycloneForecastLayer = null;
let cycloneEnvironmentLayer = null;
let lastWeatherHeading = 'Connecting to live weather data...';

const riskMetrics = [
  { key: 'wind', label: 'windRiskVal', level: 'windRiskLevel', detail: 'windRiskDetail', track: 'windRiskTrack', bar: 'windRiskBar' },
  { key: 'rainfall', label: 'rainRiskVal', level: 'rainRiskLevel', detail: 'rainRiskDetail', track: 'rainRiskTrack', bar: 'rainRiskBar' },
  { key: 'flood', label: 'floodRiskVal', level: 'floodRiskLevel', detail: 'floodRiskDetail', track: 'floodRiskTrack', bar: 'floodRiskBar' },
  { key: 'storm_surge', label: 'surgeRiskVal', level: 'surgeRiskLevel', detail: 'surgeRiskDetail', track: 'surgeRiskTrack', bar: 'surgeRiskBar' },
  { key: 'cyclone_proximity', label: 'cycloneRiskVal', level: 'cycloneRiskLevel', detail: 'cycloneRiskDetail', track: 'cycloneRiskTrack', bar: 'cycloneRiskBar' }
];

function formatRiskNumber(value, decimals = 1) {
  if (value == null || value === '') return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Number.isInteger(number) ? String(number) : number.toFixed(decimals);
}

function scoreIsZero(value) {
  return value != null && Number.isFinite(Number(value)) && Number(value) === 0;
}

function formatCycloneWind(value) {
  const speed = formatRiskNumber(value);
  return speed == null ? 'Not reported' : `${speed} km/h`;
}

function resetCycloneSelection(message) {
  const score = document.getElementById('cycloneWindIndexScore');
  const gauge = document.getElementById('cycloneWindIndexGauge');
  const level = document.getElementById('cycloneWindIndexLevel');
  const note = document.getElementById('cycloneWindIndexNote');
  if (score) score.textContent = '--';
  if (gauge) {
    gauge.style.setProperty('--gauge-angle', '0deg');
    gauge.style.setProperty('--gauge-color', '#94a3b8');
    gauge.removeAttribute('aria-valuenow');
    gauge.removeAttribute('aria-valuetext');
  }
  if (level) {
    level.textContent = 'NO LIVE STORM SELECTED';
    level.dataset.level = 'unavailable';
  }
  if (note) note.textContent = message;
  [
    ['cycloneSelectedName', 'No storm selected'],
    ['cycloneSelectedWind', 'Unavailable'],
    ['cycloneSelectedCategory', 'Unavailable'],
    ['cycloneSelectedMovement', 'Unavailable'],
    ['cycloneSelectedPosition', 'Unavailable']
  ].forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
  const source = document.getElementById('cycloneSelectedSource');
  if (source) source.textContent = 'Official feed';
  const mapStatus = document.getElementById('riskCycloneMapStatus');
  if (mapStatus) mapStatus.textContent = message;
  if (riskCycloneMapReady && window.weatherMap) window.weatherMap.clearMap('riskCycloneMap');
  cycloneForecastRequestId += 1;
  if (cycloneForecastLayer) cycloneForecastLayer.clearLayers();
  resetCycloneEnvironment(message);
}

function ensureRiskCycloneMap() {
  if (riskCycloneMapReady) return true;
  if (!window.weatherMap || typeof L === 'undefined') {
    const status = document.getElementById('riskCycloneMapStatus');
    if (status) status.textContent = 'The map library is unavailable. Live cyclone feed data can still be viewed above.';
    return false;
  }
  const map = window.weatherMap.initMap('riskCycloneMap', [20.5937, 78.9629], 3);
  if (!map) return false;
  window.weatherMap.addCycloneBasemaps('riskCycloneMap');
  cycloneForecastLayer = L.layerGroup();
  cycloneEnvironmentLayer = L.layerGroup();
  const layerControl = window.weatherMap.layerControls.riskCycloneMap;
  if (layerControl) {
    layerControl.addOverlay(cycloneForecastLayer, 'Optional: Official NHC forecast path');
    layerControl.addOverlay(cycloneEnvironmentLayer, 'Optional: Model conditions at storm');
  }
  riskCycloneMapReady = true;
  return true;
}

function addRiskCycloneMarker(cyclone, map) {
  const lat = Number(cyclone.lat);
  const lon = Number(cyclone.lon);
  const icon = L.divIcon({
    className: 'cyclone-marker-icon',
    html: '<div class="cyclone-marker-core"><span class="cyclone-marker-vortex" aria-hidden="true">🌀</span></div>',
    iconSize: [60, 60],
    iconAnchor: [30, 30]
  });
  const marker = L.marker([lat, lon], { icon });
  const popup = document.createElement('div');
  const title = document.createElement('strong');
  title.textContent = cyclone.name || 'Active cyclone';
  const wind = document.createElement('div');
  wind.textContent = `Maximum sustained wind: ${formatCycloneWind(cyclone.max_wind_speed)}`;
  const source = document.createElement('div');
  source.textContent = `Feed: ${cyclone.source || 'Official cyclone feed'}`;
  popup.append(title, wind, source);
  marker.bindPopup(popup);
  window.weatherMap.layerGroups.riskCycloneMap.addLayer(marker);
  map.flyTo([lat, lon], Math.max(map.getZoom(), 4), { animate: false });

  const speed = Number(cyclone.movement_speed);
  const bearing = window.weatherMap.parseBearing(cyclone.movement_dir);
  if (Number.isFinite(speed) && speed > 0 && bearing != null) {
    const projection = [];
    for (let hour = 0; hour <= 6; hour += 1) {
      projection.push(window.weatherMap.destinationPoint(lat, lon, bearing, speed * hour));
    }
    L.polyline(projection, {
      color: '#f97316',
      weight: 4,
      opacity: 0.9,
      dashArray: '9 10'
    }).bindTooltip('6-hour motion projection from reported movement · not an official forecast')
      .addTo(window.weatherMap.layerGroups.riskCycloneMap);
    L.circleMarker(projection[projection.length - 1], {
      radius: 6,
      color: '#fff',
      weight: 2,
      fillColor: '#f97316',
      fillOpacity: 1
    }).bindTooltip('Estimated motion projection').addTo(window.weatherMap.layerGroups.riskCycloneMap);
    const directionIcon = L.divIcon({
      className: 'cyclone-direction-icon',
      html: `<span aria-hidden="true" style="display:block;color:#9a3412;font-size:26px;font-weight:800;line-height:1;text-shadow:0 1px 3px #fff;transform:rotate(${bearing - 90}deg)">➤</span>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });
    L.marker(projection[1], { icon: directionIcon, interactive: false })
      .bindTooltip(`Reported movement direction ${cyclone.movement_dir}`)
      .addTo(window.weatherMap.layerGroups.riskCycloneMap);
  }
}

function formatModelValue(value, unit, decimals = 1) {
  const formatted = formatRiskNumber(value, decimals);
  return formatted == null ? 'Unavailable' : `${formatted}${unit}`;
}

function resetCycloneEnvironment(message = 'Model conditions are unavailable for this storm position.') {
  cycloneEnvironmentRequestId += 1;
  const fields = [
    'cycloneEnvWind',
    'cycloneEnvWindDirection',
    'cycloneEnvCloud',
    'cycloneEnvSeaLevel',
    'cycloneEnvWaves',
    'cycloneEnvSst'
  ];
  fields.forEach(id => {
    const element = document.getElementById(id);
    if (element) element.textContent = 'Unavailable';
  });
  const status = document.getElementById('cycloneEnvironmentStatus');
  const updated = document.getElementById('cycloneEnvironmentUpdated');
  if (status) status.textContent = message;
  if (updated) updated.textContent = 'No model sample';
  if (cycloneEnvironmentLayer) cycloneEnvironmentLayer.clearLayers();
}

function addCycloneEnvironmentMarker(cyclone, data) {
  if (!cycloneEnvironmentLayer) return;
  cycloneEnvironmentLayer.clearLayers();
  const lat = Number(cyclone.lat);
  const lon = Number(cyclone.lon);
  const weather = data.weather || {};
  const marine = data.marine || {};
  const popup = document.createElement('div');
  const title = document.createElement('strong');
  title.textContent = `${cyclone.name || 'Storm'} · model sample`;
  popup.appendChild(title);
  [
    ['10 m wind', formatModelValue(weather.wind_speed_10m, ' km/h')],
    ['Wind gust', formatModelValue(weather.wind_gusts_10m, ' km/h')],
    ['Wind direction', formatModelValue(weather.wind_direction_10m, '°', 0)],
    ['Cloud cover', formatModelValue(weather.cloud_cover, '%', 0)],
    ['Humidity', formatModelValue(weather.relative_humidity_2m, '%', 0)],
    ['Sea-level height', formatModelValue(marine.sea_level_height_msl, ' m')],
    ['Wave height', formatModelValue(marine.wave_height, ' m')],
    ['Wave direction', formatModelValue(marine.wave_direction, '°', 0)],
    ['Sea-surface temperature', formatModelValue(marine.sea_surface_temperature, '°C')]
  ].forEach(([label, value]) => {
    const row = document.createElement('div');
    row.textContent = `${label}: ${value}`;
    popup.appendChild(row);
  });
  const marker = L.circleMarker([lat, lon], {
    radius: 11,
    color: '#fff',
    weight: 2,
    fillColor: '#0e7490',
    fillOpacity: 0.95
  });
  marker.bindPopup(popup);
  marker.bindTooltip('Open-Meteo weather and marine model sample');
  cycloneEnvironmentLayer.addLayer(marker);
}

async function loadCycloneEnvironment(cyclone) {
  const status = document.getElementById('cycloneEnvironmentStatus');
  const updated = document.getElementById('cycloneEnvironmentUpdated');
  if (!cyclone || !Number.isFinite(Number(cyclone.lat)) || !Number.isFinite(Number(cyclone.lon))) {
    resetCycloneEnvironment('No storm coordinates are available for model sampling.');
    return;
  }
  const requestId = ++cycloneEnvironmentRequestId;
  if (status) status.textContent = 'Fetching point weather and marine model data...';
  if (updated) updated.textContent = 'Sampling reported storm coordinates';

  try {
    const result = await window.weatherApp.fetchAPI(
      `/cyclones/environment?lat=${encodeURIComponent(cyclone.lat)}&lon=${encodeURIComponent(cyclone.lon)}`
    );
    if (requestId !== cycloneEnvironmentRequestId) return;
    const weather = result.weather || {};
    const marine = result.marine || {};
    const fields = {
      cycloneEnvWind: weather.wind_speed_10m == null
        ? 'Unavailable'
        : `${formatModelValue(weather.wind_speed_10m, ' km/h')} / ${formatModelValue(weather.wind_gusts_10m, ' km/h')}`,
      cycloneEnvWindDirection: formatModelValue(weather.wind_direction_10m, '°', 0),
      cycloneEnvCloud: weather.cloud_cover == null && weather.relative_humidity_2m == null
        ? 'Unavailable'
        : `${formatModelValue(weather.cloud_cover, '%', 0)} / ${formatModelValue(weather.relative_humidity_2m, '%', 0)}`,
      cycloneEnvSeaLevel: formatModelValue(marine.sea_level_height_msl, ' m'),
      cycloneEnvWaves: marine.wave_height == null && marine.wave_direction == null
        ? 'Unavailable'
        : `${formatModelValue(marine.wave_height, ' m')} / ${formatModelValue(marine.wave_direction, '°', 0)}`,
      cycloneEnvSst: formatModelValue(marine.sea_surface_temperature, '°C')
    };
    Object.entries(fields).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
    const hasConditions = Object.keys(weather).length > 0 || Object.keys(marine).length > 0;
    if (status) {
      status.textContent = hasConditions
        ? `Model data sampled at ${Number(cyclone.lat).toFixed(2)}°, ${Number(cyclone.lon).toFixed(2)}° · weather and ocean values are forecast-model estimates, not direct observations.`
        : `Model conditions unavailable${result.errors ? `: ${Object.values(result.errors).join('; ')}` : '.'}`;
    }
    if (updated) updated.textContent = result.checked_at
      ? `Checked ${window.weatherApp.formatDateTime(result.checked_at)}`
      : 'Check time not reported';
    if (hasConditions && ensureRiskCycloneMap()) addCycloneEnvironmentMarker(cyclone, result);
  } catch (error) {
    if (requestId !== cycloneEnvironmentRequestId) return;
    console.warn('Cyclone environmental model data error:', error);
    resetCycloneEnvironment(`Could not load model conditions: ${error.message}`);
  }
}

async function loadOfficialCycloneForecast(cyclone) {
  const requestId = ++cycloneForecastRequestId;
  const mapStatus = document.getElementById('riskCycloneMapStatus');
  if (cycloneForecastLayer) cycloneForecastLayer.clearLayers();
  if (!cyclone || !cyclone.name) return;
  try {
    const result = await window.weatherApp.fetchAPI(
      `/cyclones/forecast?name=${encodeURIComponent(cyclone.name)}`
    );
    if (requestId !== cycloneForecastRequestId) return;
    if (!Array.isArray(result.coordinates) || result.coordinates.length < 2) {
      throw new Error('The official feed returned no usable forecast coordinates.');
    }
    if (!ensureRiskCycloneMap()) return;
    const points = result.coordinates.map(point => [Number(point[0]), Number(point[1])]);
    L.polyline(points, {
      color: '#2563eb',
      weight: 4,
      opacity: 0.9
    }).bindTooltip(`Official NHC forecast track · up to ${result.horizon_hours} hours`)
      .addTo(cycloneForecastLayer);
    (result.forecast_points || []).forEach(point => {
      const forecastPoint = L.circleMarker([Number(point.lat), Number(point.lon)], {
        radius: 5,
        color: '#fff',
        weight: 2,
        fillColor: '#2563eb',
        fillOpacity: 1
      });
      forecastPoint.bindTooltip(`Official forecast · +${point.hours} hours`);
      cycloneForecastLayer.addLayer(forecastPoint);
    });
    if (mapStatus) {
      mapStatus.textContent = `Latest position and official NHC forecast track loaded for ${result.storm_name || cyclone.name} · ${result.horizon_hours}-hour track · issued ${result.issuance ? window.weatherApp.formatDateTime(result.issuance) : 'time not reported'}.`;
    }
  } catch (error) {
    if (requestId !== cycloneForecastRequestId) return;
    if (mapStatus) {
      mapStatus.textContent = error.status === 404
        ? `No official NHC forecast track is available for ${cyclone.name}; the live feed position and movement remain shown.`
        : `Official NHC forecast track unavailable: ${error.message}`;
    }
  }
}

function renderCycloneOutlook(result) {
  const container = document.getElementById('cycloneOutlookList');
  const status = document.getElementById('cycloneOutlookStatus');
  if (!container) return;
  container.replaceChildren();
  const systems = Array.isArray(result.systems) ? result.systems : [];
  const unavailable = (result.sources || []).filter(source => source.status !== 'available');
  if (systems.length) {
    systems.forEach(system => {
      const card = document.createElement('article');
      card.className = 'risk-cyclone-stat';
      const region = document.createElement('h3');
      region.className = 'risk-cyclone-stat-value';
      region.textContent = `${system.region || 'Development area'} · ${system.basin || 'NHC'}`;
      const chances = document.createElement('p');
      chances.className = 'risk-source-note mt-2 mb-2';
      chances.textContent = `Formation chance: ${system.formation_chance_48h_pct}% in 48 hours · ${system.formation_chance_7d_pct == null ? '7-day chance not reported' : `${system.formation_chance_7d_pct}% in 7 days`}`;
      const description = document.createElement('p');
      description.className = 'risk-source-note mb-0';
      description.textContent = system.description || 'See the official NHC outlook for details.';
      card.append(region, chances, description);
      container.appendChild(card);
    });
  } else {
    const message = document.createElement('p');
    message.className = 'risk-source-note mb-0';
    message.textContent = unavailable.length === (result.sources || []).length
      ? 'No NHC outlook source is currently reachable. No formation status can be confirmed.'
      : 'No tropical cyclone development area is listed in the currently available NHC outlooks.';
    container.appendChild(message);
  }
  if (status) {
    const sourceSummary = (result.sources || [])
      .map(source => `${source.basin}: ${source.status}`)
      .join(' · ');
    status.textContent = `${systems.length} official development area${systems.length === 1 ? '' : 's'} reported · ${sourceSummary || 'Outlook source status unavailable'}${result.checked_at ? ` · checked ${window.weatherApp.formatDateTime(result.checked_at)}` : ''}`;
  }
}

async function loadCycloneOutlook() {
  const status = document.getElementById('cycloneOutlookStatus');
  if (status) status.textContent = 'Refreshing official NHC development outlooks...';
  try {
    const result = await window.weatherApp.fetchAPI('/cyclones/outlook');
    renderCycloneOutlook(result);
  } catch (error) {
    console.warn('NHC cyclone development outlook error:', error);
    renderCycloneOutlook({
      systems: [],
      sources: [],
      checked_at: null
    });
    if (status) status.textContent = `Official development outlook unavailable: ${error.message}`;
  }
}

function renderSelectedCyclone(cyclone, checkedAt) {
  if (!cyclone) {
    resetCycloneSelection('No matching active cyclone with live feed data was found.');
    return;
  }

  const wind = cyclone.max_wind_speed == null || cyclone.max_wind_speed === ''
    ? null
    : Number(cyclone.max_wind_speed);
  const index = cyclone.wind_intensity_index == null || cyclone.wind_intensity_index === ''
    ? null
    : Number(cyclone.wind_intensity_index);
  const hasWind = Number.isFinite(wind);
  const hasIndex = Number.isFinite(index);
  const gauge = document.getElementById('cycloneWindIndexGauge');
  const score = document.getElementById('cycloneWindIndexScore');
  const level = document.getElementById('cycloneWindIndexLevel');
  const note = document.getElementById('cycloneWindIndexNote');
  const source = document.getElementById('cycloneSelectedSource');
  const movementParts = [
    cyclone.movement_dir || null,
    cyclone.movement_speed == null ? null : `${formatRiskNumber(cyclone.movement_speed)} km/h`
  ].filter(Boolean);

  if (score) score.textContent = hasIndex ? `${index}%` : '--';
  if (level) {
    level.textContent = hasIndex
      ? index >= 75 ? 'EXTREME WIND' : index >= 50 ? 'HIGH WIND' : index >= 25 ? 'MODERATE WIND' : 'LOW WIND'
      : 'WIND NOT REPORTED';
    level.dataset.level = !hasIndex ? 'unavailable' : index >= 75 ? 'extreme' : index >= 50 ? 'high' : index >= 25 ? 'moderate' : 'low';
  }
  if (gauge) {
    gauge.style.setProperty('--gauge-angle', `${hasIndex ? index * 3.6 : 0}deg`);
    gauge.style.setProperty('--gauge-color', !hasIndex ? '#94a3b8' : index >= 75 ? '#dc2626' : index >= 50 ? '#ea580c' : index >= 25 ? '#d97706' : '#059669');
    if (hasIndex) {
      gauge.setAttribute('aria-valuenow', String(index));
      gauge.setAttribute('aria-valuetext', `${index}% reported cyclone wind-intensity index`);
    } else {
      gauge.removeAttribute('aria-valuenow');
      gauge.removeAttribute('aria-valuetext');
    }
  }
  if (note) {
    note.textContent = hasIndex
      ? `Official feed reports maximum sustained wind of ${formatCycloneWind(wind)}. The percentage is the app's wind-hazard index, not cyclone formation, landfall, or damage probability.`
      : 'The selected live feed does not report maximum sustained wind, so no wind index is estimated.';
  }

  const values = {
    cycloneSelectedName: cyclone.name || 'Unnamed active system',
    cycloneSelectedWind: formatCycloneWind(wind),
    cycloneSelectedCategory: cyclone.category || cyclone.intensity || 'Not reported',
    cycloneSelectedMovement: movementParts.length ? movementParts.join(' · ') : 'Not reported',
    cycloneSelectedPosition: Number.isFinite(Number(cyclone.lat)) && Number.isFinite(Number(cyclone.lon))
      ? `${Number(cyclone.lat).toFixed(2)}°, ${Number(cyclone.lon).toFixed(2)}°`
      : 'Not reported'
  };
  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
  if (source) source.textContent = [cyclone.source, cyclone.basin, checkedAt ? `checked ${window.weatherApp.formatDateTime(checkedAt)}` : null].filter(Boolean).join(' · ');

  const mapStatus = document.getElementById('riskCycloneMapStatus');
  if (ensureRiskCycloneMap()) {
    const map = window.weatherMap.maps.riskCycloneMap;
    window.weatherMap.clearMap('riskCycloneMap');
    if (Number.isFinite(Number(cyclone.lat)) && Number.isFinite(Number(cyclone.lon))) {
      addRiskCycloneMarker(cyclone, map);
      loadCycloneEnvironment(cyclone);
      loadOfficialCycloneForecast(cyclone);
      if (mapStatus) {
        mapStatus.textContent = `Latest position from ${cyclone.source || 'official feed'} · ${values.cycloneSelectedPosition} · ${checkedAt ? `feed checked ${window.weatherApp.formatDateTime(checkedAt)}` : 'check time unavailable'}.`;
      }
    } else if (mapStatus) {
      mapStatus.textContent = 'The selected active storm has no coordinates in the feed, so it cannot be plotted.';
      resetCycloneEnvironment('No storm coordinates are available for model sampling.');
    }
    window.setTimeout(() => map.invalidateSize(), 50);
  }
}

function populateCycloneRiskSelect(cyclones, selectedIndex = 0) {
  const select = document.getElementById('riskCycloneSelect');
  if (!select) return;
  select.replaceChildren();
  cyclones.forEach((cyclone, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = `${cyclone.name || cyclone.identifier || 'Unnamed storm'} · ${cyclone.category || cyclone.intensity || 'Active system'}`;
    select.appendChild(option);
  });
  if (cyclones.length) select.value = String(Math.max(0, Math.min(selectedIndex, cyclones.length - 1)));
  else {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No active cyclone found';
    select.appendChild(option);
  }
}

async function refreshCycloneRisk(query = '') {
  const requestId = ++cycloneFeedRequestId;
  const status = document.getElementById('cycloneRiskLiveStatus');
  const dot = document.getElementById('cycloneRiskLiveDot');
  const context = document.getElementById('cycloneRiskFeedContext');
  const checkedAtElement = document.getElementById('cycloneRiskCheckedAt');
  const button = document.getElementById('refreshCycloneRiskBtn');
  if (status) status.textContent = 'Checking live official cyclone feeds...';
  if (dot) dot.className = 'risk-live-dot';
  if (button) button.disabled = true;

  try {
    const result = await window.weatherApp.fetchAPI('/cyclones/active');
    if (requestId !== cycloneFeedRequestId) return;
    activeRiskCyclones = Array.isArray(result.cyclones) ? result.cyclones : [];
    const term = query.trim().toLocaleLowerCase();
    visibleRiskCyclones = term
      ? activeRiskCyclones.filter(cyclone =>
        [cyclone.name, cyclone.identifier, cyclone.basin]
          .filter(Boolean)
          .some(value => String(value).toLocaleLowerCase().includes(term))
      )
      : activeRiskCyclones;
    const checkedAt = result.checked_at || null;
    riskCycloneCheckedAt = checkedAt;
    if (checkedAtElement) checkedAtElement.textContent = checkedAt
      ? `Checked ${window.weatherApp.formatDateTime(checkedAt)}`
      : 'Check time not reported';
    if (context) context.textContent = `${(result.sources_checked || []).join(', ') || 'Official source not reported'} · ${result.message || 'Feed check complete.'}`;

    if (!Array.isArray(result.sources_checked) || !result.sources_checked.length) {
      throw new Error(result.message || 'No official cyclone source responded.');
    }
    ensureRiskCycloneMap();

    if (status) status.textContent = visibleRiskCyclones.length
      ? `LIVE OFFICIAL DATA · ${visibleRiskCyclones.length} active system${visibleRiskCyclones.length === 1 ? '' : 's'}`
      : term
        ? 'LIVE FEEDS CHECKED · no active storm matched that name'
        : 'LIVE FEEDS CHECKED · no active cyclone reported';
    if (dot) dot.className = visibleRiskCyclones.length ? 'risk-live-dot is-live' : 'risk-live-dot';
    const selectIndex = 0;
    populateCycloneRiskSelect(visibleRiskCyclones, selectIndex);
    renderSelectedCyclone(visibleRiskCyclones[0] || null, checkedAt);
  } catch (error) {
    if (requestId !== cycloneFeedRequestId) return;
    console.warn('Live cyclone feed error:', error);
    activeRiskCyclones = [];
    visibleRiskCyclones = [];
    populateCycloneRiskSelect([]);
    if (status) status.textContent = 'LIVE CYCLONE DATA UNAVAILABLE';
    if (dot) dot.className = 'risk-live-dot is-error';
    if (context) context.textContent = error.message;
    if (checkedAtElement) checkedAtElement.textContent = 'Unable to confirm current storm conditions';
    resetCycloneSelection(`Official cyclone feeds could not be reached: ${error.message}`);
  } finally {
    if (requestId === cycloneFeedRequestId && button) button.disabled = false;
  }
}

function setRiskMetric(metric, scoreValue, detail, state = 'assessed') {
  const scoreElement = document.getElementById(metric.label);
  const levelElement = document.getElementById(metric.level);
  const detailElement = document.getElementById(metric.detail);
  const trackElement = document.getElementById(metric.track);
  const barElement = document.getElementById(metric.bar);
  const score = scoreValue == null || !Number.isFinite(Number(scoreValue))
    ? null
    : Math.max(0, Math.min(100, Number(scoreValue)));

  if (state === 'not-assessed') {
    if (scoreElement) scoreElement.textContent = 'Not assessed';
    if (levelElement) {
      levelElement.textContent = 'NOT ASSESSED';
      levelElement.dataset.level = 'not-assessed';
    }
    if (detailElement) detailElement.textContent = detail;
    if (trackElement) {
      trackElement.dataset.state = 'not-assessed';
      trackElement.removeAttribute('aria-valuenow');
      trackElement.removeAttribute('aria-valuetext');
    }
    if (barElement) barElement.style.width = '0%';
    return;
  }

  if (score == null) {
    if (scoreElement) scoreElement.textContent = 'Unavailable';
    if (levelElement) {
      levelElement.textContent = 'NO DATA';
      levelElement.dataset.level = 'unavailable';
    }
    if (detailElement) detailElement.textContent = detail || 'Required live measurement unavailable.';
    if (trackElement) {
      trackElement.dataset.state = 'unavailable';
      trackElement.removeAttribute('aria-valuenow');
      trackElement.removeAttribute('aria-valuetext');
    }
    if (barElement) barElement.style.width = '0%';
    return;
  }

  const level = score < 25 ? 'Low' : score < 50 ? 'Moderate' : score < 75 ? 'High' : 'Extreme';
  const color = score >= 75 ? '#dc2626' : score >= 50 ? '#ea580c' : score >= 25 ? '#d97706' : '#059669';
  if (scoreElement) scoreElement.textContent = `${score}%`;
  if (levelElement) {
    levelElement.textContent = level.toUpperCase();
    levelElement.dataset.level = level.toLowerCase();
  }
  if (detailElement) detailElement.textContent = detail;
  if (trackElement) {
    trackElement.dataset.state = 'assessed';
    trackElement.setAttribute('aria-valuenow', String(score));
    trackElement.setAttribute('aria-valuetext', `${score} out of 100, ${level} risk`);
    trackElement.style.setProperty('--risk-marker-position', `${Math.min(96, Math.max(4, score))}%`);
    trackElement.style.setProperty('--bar-color', color);
  }
  if (barElement) {
    barElement.style.width = `${score}%`;
    barElement.style.setProperty('--bar-color', color);
  }
}

function renderRecommendations(recommendations, unavailable = false) {
  const container = document.getElementById('recommendationsList');
  if (!container) return;
  container.replaceChildren();

  if (unavailable) {
    const message = document.createElement('p');
    message.className = 'risk-source-note';
    message.textContent = 'Safety recommendations are unavailable until a live assessment is received.';
    container.appendChild(message);
    return;
  }

  if (!Array.isArray(recommendations) || !recommendations.length) {
    const message = document.createElement('p');
    message.className = 'risk-source-note';
    message.textContent = 'No recommendations were returned for this assessment.';
    container.appendChild(message);
    return;
  }

  const list = document.createElement('ul');
  list.className = 'risk-text-list';
  recommendations.forEach(recommendation => {
    const entry = document.createElement('li');
    entry.textContent = recommendation;
    list.appendChild(entry);
  });
  container.appendChild(list);
}

function renderContributingFactors(factors, assessmentAvailable) {
  const container = document.getElementById('contributingFactorsList');
  const count = document.getElementById('riskFactorsCount');
  if (!container) return;
  container.replaceChildren();

  const list = Array.isArray(factors) ? factors : [];
  if (count) count.textContent = assessmentAvailable
    ? `${list.length} elevated ${list.length === 1 ? 'factor' : 'factors'}`
    : 'No live assessment';

  if (list.length) {
    list.forEach(factor => {
      const entry = document.createElement('div');
      entry.className = 'risk-factor';
      const name = String(factor.factor || 'Weather hazard').replaceAll('_', ' ');
      entry.textContent = `${name}: ${factor.score}% (${factor.level || 'Elevated'})`;
      container.appendChild(entry);
    });
    return;
  }

  const message = document.createElement('p');
  message.className = 'risk-source-note mb-0';
  message.textContent = assessmentAvailable
    ? 'No elevated contributing hazards in the available live measurements. Zero scores are valid results when current conditions are below model thresholds.'
    : 'Contributing hazards cannot be determined until a live assessment is available.';
  container.appendChild(message);
}

function renderLiveConditions(summary) {
  const format = (value, unit, decimals = 1) => {
    const number = formatRiskNumber(value, decimals);
    return number == null ? 'Unavailable' : `${number}${unit}`;
  };
  const values = {
    riskTempValue: format(summary.temperature_c, '°C'),
    riskHumidityValue: format(summary.humidity_pct, '%', 0),
    riskWindValue: format(summary.wind_speed_kmh, ' km/h'),
    riskRainValue: format(summary.rainfall_mm, ' mm'),
    riskPressureValue: format(summary.pressure_hpa, ' hPa')
  };
  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

function setUnavailableState(message) {
  const score = document.getElementById('riskScore');
  const badge = document.getElementById('riskLevelBadge');
  const gauge = document.getElementById('riskGauge');
  const overview = document.getElementById('riskOverviewMessage');
  const liveStatus = document.getElementById('riskLiveStatus');
  const dot = document.getElementById('riskLiveDot');
  const context = document.getElementById('riskDataContext');
  const updated = document.getElementById('riskUpdatedAt');

  if (score) score.textContent = '--';
  if (badge) {
    badge.textContent = 'ASSESSMENT UNAVAILABLE';
    badge.dataset.level = 'unavailable';
  }
  if (gauge) {
    gauge.style.setProperty('--gauge-angle', '0deg');
    gauge.style.setProperty('--gauge-color', '#94a3b8');
    gauge.removeAttribute('aria-valuenow');
  }
  if (overview) overview.textContent = 'No risk score is shown because the live assessment could not be completed.';
  if (liveStatus) liveStatus.textContent = 'Live assessment unavailable';
  if (dot) dot.className = 'risk-live-dot is-error';
  if (context) context.textContent = message;
  if (updated) updated.textContent = 'No current observation received';
  renderLiveConditions({});

  riskMetrics.forEach(metric => setRiskMetric(metric, null, 'Live data unavailable.'));
  renderRecommendations([], true);
  renderContributingFactors([], false);
}

async function loadRiskAssessment(cityName) {
  const city = cityName || window.weatherApp.currentCity || 'Indore';
  const requestId = ++riskRequestId;
  const dashboard = document.getElementById('riskDashboard');
  const header = document.getElementById('riskCityHeader');
  const weatherView = document.getElementById('weatherRiskView');
  const input = document.getElementById('riskCityInput');
  const liveStatus = document.getElementById('riskLiveStatus');
  const dot = document.getElementById('riskLiveDot');
  const updated = document.getElementById('riskUpdatedAt');
  const refreshButton = document.getElementById('refreshRiskBtn');

  lastWeatherHeading = `Live hazard assessment for ${city}`;
  if (header && !weatherView.hidden) header.textContent = lastWeatherHeading;
  if (input && document.activeElement !== input) input.value = city;
  if (liveStatus) liveStatus.textContent = 'Refreshing live weather and cyclone feeds...';
  if (dot) dot.className = 'risk-live-dot';
  if (dashboard) dashboard.classList.add('risk-loading');
  if (refreshButton) refreshButton.disabled = true;

  try {
    const response = await window.weatherApp.fetchAPI(
      `/risk/assessment?city=${encodeURIComponent(city)}`
    );
    if (requestId !== riskRequestId) return;
    const data = response.data || {};
    const summary = data.weather_summary || {};
    const riskScores = data.individual_risks || {};
    const cyclone = data.cyclone_details || {};
    const cityLabel = [data.city || city, data.country].filter(Boolean).join(', ');
    const locationPrecision = data.location_precision === 'administrative-area reference point'
      ? ' · State/region reference point (not a state-wide average)'
      : '';
    const observed = data.observed_at
      ? window.weatherApp.formatDateTime(data.observed_at)
      : 'Observation time not supplied';
    const feedChecked = data.cyclone_feed_checked_at
      ? window.weatherApp.formatDateTime(data.cyclone_feed_checked_at)
      : null;

    lastWeatherHeading = `Live hazard assessment for ${cityLabel}`;
    if (header && !weatherView.hidden) header.textContent = lastWeatherHeading;
    if (document.getElementById('riskDataContext')) {
      document.getElementById('riskDataContext').textContent =
        `${data.data_source || 'Weather source not reported'} · observed ${observed}${locationPrecision}`;
    }
    if (updated) {
      updated.textContent = data.cyclone_feed_status === 'available'
        ? `Cyclone feeds checked ${feedChecked || 'during this assessment'}`
        : 'Cyclone feed unavailable; weather readings are shown separately';
    }
    if (liveStatus) {
      liveStatus.textContent = data.cyclone_feed_status === 'available'
        ? 'LIVE DATA RECEIVED · weather and cyclone feeds checked'
        : 'LIVE WEATHER RECEIVED · cyclone feed unavailable';
    }
    if (dot) dot.className = data.cyclone_feed_status === 'available'
      ? 'risk-live-dot is-live'
      : 'risk-live-dot is-error';

    renderLiveConditions(summary);

    const weatherSummary = document.getElementById('riskWeatherSummary');
    if (weatherSummary) {
      weatherSummary.textContent =
        `Conditions: ${summary.weather_condition || 'Not reported'} · Source: ${data.data_source || 'Not reported'} · Weather observation: ${observed} · ` +
        `Country: ${data.country || 'Not reported'}${locationPrecision}. ` +
        'Live weather values are provider model estimates; hazard scores are simplified model indexes, not probabilities.';
    }

    const hasScore = data.overall_score != null && Number.isFinite(Number(data.overall_score));
    const overall = hasScore ? Math.max(0, Math.min(100, Number(data.overall_score))) : null;
    const level = hasScore ? (data.risk_level || 'Low') : 'Unavailable';
    const scoreElement = document.getElementById('riskScore');
    const badge = document.getElementById('riskLevelBadge');
    const gauge = document.getElementById('riskGauge');
    const overview = document.getElementById('riskOverviewMessage');

    if (scoreElement) scoreElement.textContent = overall == null ? '--' : `${overall}%`;
    if (badge) {
      badge.textContent = hasScore ? `${level.toUpperCase()} · LIVE MODEL` : 'ASSESSMENT UNAVAILABLE';
      badge.dataset.level = level.toLowerCase();
    }
    if (gauge) {
      gauge.style.setProperty('--gauge-angle', `${(overall || 0) * 3.6}deg`);
      gauge.style.setProperty('--gauge-color',
        overall == null ? '#94a3b8' : overall >= 75 ? '#dc2626' : overall >= 50 ? '#ea580c' : overall >= 25 ? '#d97706' : '#059669'
      );
      if (overall == null) gauge.removeAttribute('aria-valuenow');
      else {
        gauge.setAttribute('aria-valuenow', String(overall));
        gauge.setAttribute('aria-valuetext', `${overall} out of 100, ${level} risk`);
      }
    }
    if (overview) {
      overview.textContent = overall == null
        ? 'The provider did not return enough measurements to calculate a composite score.'
        : overall === 0
          ? 'No elevated hazards were identified in the available live conditions. Zero is a valid model result, not missing data.'
          : `Composite score from the available weather measurements and ${data.cyclone_feed_status === 'available' ? 'checked cyclone feed' : 'available hazard inputs'}. Follow official warnings.`;
    }

    const cycloneName = cyclone.name ? `${cyclone.name}` : null;
    const cycloneDistance = cyclone.distance_km == null
      ? 'distance unavailable'
      : `${formatRiskNumber(cyclone.distance_km)} km from this location`;
    const cycloneMovement = cyclone.movement_dir
      ? ` · moving ${cyclone.movement_dir}${cyclone.movement_speed_kmh == null ? '' : ` at ${cyclone.movement_speed_kmh} km/h`}`
      : '';
    const windSpeed = summary.wind_speed_kmh;
    const windGust = summary.wind_gust_kmh;
    const rainfall = summary.rainfall_mm;
    const detailFor = {
      wind: windSpeed == null
        ? 'Wind risk cannot be calculated: provider returned no wind speed.'
        : scoreIsZero(riskScores.wind)
          ? `Live wind: ${formatRiskNumber(windSpeed)} km/h${windGust == null ? '' : ` · gust ${formatRiskNumber(windGust)} km/h`} — the model uses sustained wind, which is below its 20 km/h elevated-risk threshold.`
          : `Live wind: ${formatRiskNumber(windSpeed)} km/h${windGust == null ? '' : ` · gust ${formatRiskNumber(windGust)} km/h`} · sustained wind reached an elevated threshold.`,
      rainfall: rainfall == null
        ? 'Precipitation risk cannot be calculated: provider returned no current precipitation.'
        : scoreIsZero(riskScores.rainfall)
          ? `Live current precipitation: ${formatRiskNumber(rainfall)} mm — below the model's 2.5 mm rainfall-risk threshold.`
          : `Live current precipitation: ${formatRiskNumber(rainfall)} mm · elevated rainfall threshold reached.`,
      flood: rainfall == null
        ? 'Flood indicator unavailable because current precipitation was not returned.'
        : scoreIsZero(riskScores.flood)
          ? `Live precipitation input: ${formatRiskNumber(rainfall)} mm — below the model's 5 mm flood-indicator threshold. This is not a local flood forecast.`
          : `Live precipitation input: ${formatRiskNumber(rainfall)} mm · simplified indicator only, not a local flood forecast.`,
      storm_surge: !data.is_coastal
        ? 'Not assessed: this location is not classified as coastal by the risk model.'
        : scoreIsZero(riskScores.storm_surge)
          ? `Live inputs: wind ${windSpeed == null ? 'unavailable' : `${formatRiskNumber(windSpeed)} km/h`} · pressure ${summary.pressure_hpa == null ? 'unavailable' : `${formatRiskNumber(summary.pressure_hpa)} hPa`} — no elevated signal in this simplified coastal model.`
          : `Live inputs: wind ${windSpeed == null ? 'unavailable' : `${formatRiskNumber(windSpeed)} km/h`} · pressure ${summary.pressure_hpa == null ? 'unavailable' : `${formatRiskNumber(summary.pressure_hpa)} hPa`}.`,
      cyclone_proximity: data.cyclone_feed_status !== 'available'
        ? 'Not assessed: official cyclone feeds could not be checked.'
        : cycloneName
          ? `${cycloneName} · ${cycloneDistance}${cycloneMovement} · ${cyclone.source || 'official feed'}${scoreIsZero(riskScores.cyclone_proximity) ? ' · outside the model\'s 1,000 km proximity bands.' : '.'}`
          : 'Official feeds checked; no active cyclone with a reportable position was returned, so proximity risk is 0%.'
    };

    riskMetrics.forEach(metric => {
      const notAssessed = metric.key === 'storm_surge' && !data.is_coastal;
      const score = riskScores[metric.key];
      setRiskMetric(
        metric,
        notAssessed ? null : score,
        detailFor[metric.key],
        notAssessed ? 'not-assessed' : 'assessed'
      );
    });

    renderRecommendations(data.recommendations, !hasScore);
    renderContributingFactors(data.contributing_factors, hasScore);
  } catch (error) {
    if (requestId !== riskRequestId) return;
    console.warn('Risk assessment error:', error);
    setUnavailableState(`Could not load live data for ${city}: ${error.message}`);
  } finally {
    if (requestId === riskRequestId) {
      if (dashboard) dashboard.classList.remove('risk-loading');
      if (refreshButton) refreshButton.disabled = false;
    }
  }
}

window.reloadCurrentPageData = function(city) {
  loadRiskAssessment(city);
};

document.addEventListener('DOMContentLoaded', () => {
  loadRiskAssessment();

  const weatherView = document.getElementById('weatherRiskView');
  const cycloneView = document.getElementById('cycloneRiskView');
  const weatherTab = document.getElementById('weatherRiskTab');
  const cycloneTab = document.getElementById('cycloneRiskTab');
  const cityActions = document.getElementById('riskCityActions');
  const header = document.getElementById('riskCityHeader');
  const cycloneSearch = document.getElementById('cycloneSearchInput');
  const cycloneSearchButton = document.getElementById('searchCycloneBtn');
  const cycloneRefreshButton = document.getElementById('refreshCycloneRiskBtn');
  const cycloneSelect = document.getElementById('riskCycloneSelect');

  const selectRiskView = view => {
    const showCyclones = view === 'cyclone';
    weatherView.hidden = showCyclones;
    cycloneView.hidden = !showCyclones;
    cityActions.hidden = showCyclones;
    weatherTab.setAttribute('aria-selected', String(!showCyclones));
    cycloneTab.setAttribute('aria-selected', String(showCyclones));
    if (header) {
      header.textContent = showCyclones
        ? 'Cyclone tracker · live positions from official feeds'
        : lastWeatherHeading;
    }
    if (showCyclones) {
      if (ensureRiskCycloneMap()) {
        window.setTimeout(
          () => window.weatherMap.maps.riskCycloneMap.invalidateSize(),
          50
        );
      }
      loadCycloneOutlook();
      if (!activeRiskCyclones.length) refreshCycloneRisk(cycloneSearch.value);
    }
  };

  weatherTab.addEventListener('click', () => selectRiskView('weather'));
  cycloneTab.addEventListener('click', () => selectRiskView('cyclone'));

  const runButton = document.getElementById('runRiskAssessmentBtn');
  const refreshButton = document.getElementById('refreshRiskBtn');
  const input = document.getElementById('riskCityInput');
  const assessInput = () => {
    const city = input && input.value.trim();
    if (!city) {
      window.weatherApp.showToast('Enter a city and country to assess.', 'warning');
      return;
    }
    window.weatherApp.handleCitySearch(city);
  };

  if (runButton && input) {
    runButton.addEventListener('click', assessInput);
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') assessInput();
    });
  }
  if (refreshButton) {
    refreshButton.addEventListener('click', () => loadRiskAssessment());
  }
  const searchCyclones = () => refreshCycloneRisk(cycloneSearch.value);
  cycloneSearchButton.addEventListener('click', searchCyclones);
  cycloneRefreshButton.addEventListener('click', searchCyclones);
  cycloneSearch.addEventListener('keydown', event => {
    if (event.key === 'Enter') searchCyclones();
  });
  cycloneSelect.addEventListener('change', () => {
    const index = Number(cycloneSelect.value);
    if (Number.isInteger(index) && visibleRiskCyclones[index]) {
      renderSelectedCyclone(visibleRiskCyclones[index], riskCycloneCheckedAt);
    } else {
      resetCycloneSelection('No matching active cyclone with live feed data was found.');
    }
  });

  window.setInterval(() => {
    if (!cycloneView.hidden) {
      refreshCycloneRisk(cycloneSearch.value);
      loadCycloneOutlook();
    }
  }, 5 * 60 * 1000);
});
