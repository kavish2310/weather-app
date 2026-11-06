/**
 * WeatherIQ - Cyclone Tracking & Geospatial Analysis Controller
 */

let activeCyclonesList = [];
let selectedTrackPoints = [];

// Historical cyclone track dataset for evaluation & simulation
const BENCHMARK_CYCLONES = [
  {
    id: 101,
    name: 'AMPHAN',
    identifier: 'BOB-01-2020',
    category: 'Super Cyclonic Storm',
    max_wind_speed: 260,
    movement_dir: 'NNE',
    movement_speed: 18,
    lat: 18.5,
    lon: 86.8,
    basin: 'Bay of Bengal',
    source: 'IMD Best Track Archive',
    track: [
      { lat: 10.5, lon: 86.5, timestamp: 'Day -3' },
      { lat: 13.2, lon: 86.3, timestamp: 'Day -2' },
      { lat: 16.0, lon: 86.5, timestamp: 'Day -1' },
      { lat: 18.5, lon: 86.8, timestamp: 'Observed Eye' }
    ],
    forecast: [
      { lat: 18.5, lon: 86.8 },
      { lat: 20.8, lon: 87.8 },
      { lat: 21.9, lon: 88.4 },
      { lat: 23.5, lon: 89.2 }
    ]
  },
  {
    id: 102,
    name: 'BIPARJOY',
    identifier: 'ARB-01-2023',
    category: 'Extremely Severe Cyclonic Storm',
    max_wind_speed: 165,
    movement_dir: 'NNE',
    movement_speed: 12,
    lat: 21.0,
    lon: 66.8,
    basin: 'Arabian Sea',
    source: 'IMD Best Track Archive',
    track: [
      { lat: 13.0, lon: 66.2, timestamp: 'Day -3' },
      { lat: 16.5, lon: 67.4, timestamp: 'Day -2' },
      { lat: 19.0, lon: 67.0, timestamp: 'Day -1' },
      { lat: 21.0, lon: 66.8, timestamp: 'Observed Eye' }
    ],
    forecast: [
      { lat: 21.0, lon: 66.8 },
      { lat: 22.4, lon: 68.1 },
      { lat: 23.2, lon: 68.8 }
    ]
  }
];

async function loadCyclonePage() {
  window.weatherMap.initMap('cycloneTrackingMap', [18.0, 80.0], 5);

  const container = document.getElementById('activeCyclonesContainer');
  const badge = document.getElementById('cycloneCountBadge');
  const select = document.getElementById('arrivalCycloneSelect');

  try {
    const res = await window.weatherApp.fetchAPI('/cyclones/active');
    activeCyclonesList = (res.cyclones || []).filter(c => c.name && c.lat && c.lon);

    if (activeCyclonesList.length > 0) {
      if (badge) {
        badge.textContent = `${activeCyclonesList.length} Active System(s)`;
        badge.className = 'badge bg-danger';
      }
      renderActiveCyclones(container, activeCyclonesList);
      populateSelect(select, activeCyclonesList);
      plotCyclonesOnMap(activeCyclonesList);
    } else {
      if (!res.sources_checked || !res.sources_checked.length) {
        throw new Error('No authoritative cyclone feed could be reached.');
      }
      if (badge) {
        badge.textContent = '0 Active (Calm)';
        badge.className = 'badge bg-success';
      }
      renderCalmWithBenchmarks(container, res.message);
      populateSelect(select, BENCHMARK_CYCLONES);
      plotBenchmark(BENCHMARK_CYCLONES[0]);
    }
  } catch (err) {
    console.error('Error fetching cyclones:', err);
    if (badge) {
      badge.textContent = 'Live status unavailable';
      badge.className = 'badge bg-warning text-dark';
    }
    if (container) {
      container.innerHTML = `
        <div class="alert alert-warning" role="status">
          Live cyclone status is unavailable: ${err.message}. No current storm status can be confirmed until an official feed responds.
        </div>
        <div class="text-muted" style="font-size:12px;">Historical reference tracks are hidden while live status is unavailable.</div>
      `;
    }
  }

  plotReferenceCoastalCities();
}

function renderCalmWithBenchmarks(container, message) {
  if (!container) return;
  container.innerHTML = `
    <div style="padding:16px;">
      <div class="alert alert-success d-flex align-items-center gap-2 mb-3" style="background:#ecfdf5; border-color:#10b981; color:#065f46; font-size:13px;">
        <span>✅</span>
        <div>
          <strong>Live Telemetry Status:</strong> ${message || 'Calm maritime basin. No active tropical cyclones detected.'}
        </div>
      </div>

      <div style="font-size:12px; color:var(--color-text-muted); margin-bottom:12px;">
        Historical reference examples (not live systems):
      </div>

      <div class="d-flex flex-column gap-2">
        ${BENCHMARK_CYCLONES.map(c => `
          <div style="background:var(--color-bg-tertiary); border:1px solid var(--color-border); border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:18px;">🌀</span>
                <strong style="color:#b91c1c;">${c.name}</strong>
                <span class="badge bg-secondary" style="font-size:10px;">${c.category}</span>
              </div>
              <div style="font-size:11px; color:var(--color-text-muted); margin-top:4px;">
                Max Winds: ${c.max_wind_speed} km/h &middot; Basin: ${c.basin} &middot; Track: ${c.movement_dir} @ ${c.movement_speed} km/h
              </div>
            </div>
            <button class="btn btn-sm btn-outline-primary" onclick="loadBenchmarkTrack(${c.id})" style="font-size:12px;">
              Inspect Track
            </button>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function renderActiveCyclones(container, cyclones) {
  if (!container) return;
  container.innerHTML = cyclones.map(c => `
    <div style="padding:16px; border-bottom:1px solid var(--color-border); display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">
      <div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
          <span style="font-size:20px;">🌀</span>
          <h5 style="margin:0; font-weight:700; color:#b91c1c;">${c.name}</h5>
          <span class="badge bg-secondary" style="font-size:11px;">${c.identifier || c.basin}</span>
        </div>
        <div style="font-size:13px; color:var(--color-text-primary); margin-bottom:6px;">
          <strong>Intensity:</strong> ${c.category || 'Tropical Cyclone'} &middot;
          <strong>Max Wind:</strong> ${c.max_wind_speed || '--'} km/h
        </div>
        <div style="font-size:12px; color:var(--color-text-muted);">
          Position: ${c.lat.toFixed(2)}°N, ${c.lon.toFixed(2)}°E &middot;
          Track: ${c.movement_dir || 'N/A'} @ ${c.movement_speed || '--'} km/h
        </div>
      </div>
      <button class="btn btn-sm btn-outline-primary" onclick="focusCyclone(${c.lat}, ${c.lon})">
        Center Map
      </button>
    </div>
  `).join('');
}

function populateSelect(select, cyclones) {
  if (!select) return;
  select.innerHTML = cyclones.map(c => `
    <option value="${c.id || c.name}">${c.name} (${c.category})</option>
  `).join('');
}

function plotCyclonesOnMap(cyclones) {
  cyclones.forEach(c => {
    window.weatherMap.addCycloneMarker('cycloneTrackingMap', c);
  });
  if (cyclones.length > 0 && cyclones[0].lat && cyclones[0].lon) {
    window.weatherMap.flyTo('cycloneTrackingMap', cyclones[0].lat, cyclones[0].lon, 6);
  }
}

function plotBenchmark(c) {
  window.weatherMap.clearMap('cycloneTrackingMap');
  plotReferenceCoastalCities();

  window.weatherMap.addCycloneMarker('cycloneTrackingMap', c);

  if (c.track && c.track.length > 1) {
    window.weatherMap.drawTrack('cycloneTrackingMap', c.track, false);
  }
  if (c.forecast && c.forecast.length > 1) {
    window.weatherMap.drawTrack('cycloneTrackingMap', c.forecast, true);
  }

  window.weatherMap.flyTo('cycloneTrackingMap', c.lat, c.lon, 6);
}

function loadBenchmarkTrack(cycloneId) {
  const c = BENCHMARK_CYCLONES.find(b => b.id === cycloneId);
  if (c) {
    plotBenchmark(c);
    const select = document.getElementById('arrivalCycloneSelect');
    if (select) select.value = c.id;
    window.weatherApp.showToast(`Loaded track for Cyclone ${c.name} on map.`, 'info');
  }
}

function plotReferenceCoastalCities() {
  const coastal = [
    { name: 'Mumbai', lat: 19.0760, lon: 72.8777 },
    { name: 'Visakhapatnam', lat: 17.6868, lon: 83.2185 },
    { name: 'Chennai', lat: 13.0827, lon: 80.2707 },
    { name: 'Puri / Bhubaneswar', lat: 19.8135, lon: 85.8312 },
    { name: 'Kolkata', lat: 22.5726, lon: 88.3639 },
    { name: 'Surat', lat: 21.1702, lon: 72.8311 }
  ];

  coastal.forEach(c => {
    window.weatherMap.addWeatherMarker(
      'cycloneTrackingMap',
      c.lat,
      c.lon,
      c.name,
      'Monitoring',
      'Coastal Station',
      '⚓'
    );
  });
}

function focusCyclone(lat, lon) {
  window.weatherMap.flyTo('cycloneTrackingMap', lat, lon, 7);
}

document.addEventListener('DOMContentLoaded', () => {
  loadCyclonePage();

  const refreshBtn = document.getElementById('refreshCyclonesBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      window.weatherApp.showToast('Re-polling NOAA, JTWC, and IMD feeds...', 'info');
      loadCyclonePage();
    });
  }

  const calcBtn = document.getElementById('calcArrivalBtn');
  if (calcBtn) {
    calcBtn.addEventListener('click', () => {
      const cityVal = document.getElementById('arrivalCitySelect').value;
      const [latStr, lonStr, cityName] = cityVal.split(',');
      const tLat = parseFloat(latStr);
      const tLon = parseFloat(lonStr);

      const cycVal = document.getElementById('arrivalCycloneSelect').value;
      let c = activeCyclonesList.find(x => String(x.id) === String(cycVal) || x.name === cycVal);
      if (!c) {
        c = BENCHMARK_CYCLONES.find(x => String(x.id) === String(cycVal)) || BENCHMARK_CYCLONES[0];
      }

      const resBox = document.getElementById('arrivalResultsContainer');
      const title = document.getElementById('arrivalResultTitle');
      const distEl = document.getElementById('arrDistance');
      const dirEl = document.getElementById('arrDirection');
      const speedEl = document.getElementById('arrSpeed');
      const winEl = document.getElementById('arrWindow');

      // Haversine calculation
      const R = 6371;
      const dLat = (tLat - c.lat) * Math.PI / 180;
      const dLon = (tLon - c.lon) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(c.lat * Math.PI / 180) * Math.cos(tLat * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const dist = Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)));

      const speed = c.movement_speed || 15;
      const hours = Math.round(dist / speed);

      title.textContent = `Kinematic Arrival Window for ${cityName} (${c.name})`;
      distEl.textContent = `${dist} km from current coordinates`;
      dirEl.textContent = `${c.movement_dir || 'NNE'} forward propagation`;
      speedEl.textContent = `${speed} km/h forward translation`;
      winEl.textContent = `Estimated landfall window: ${hours} - ${hours + 8} hours`;
      resBox.style.display = 'block';
    });
  }
});
