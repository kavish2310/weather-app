/**
 * WeatherIQ - Cyclone Tracking & Geospatial Analysis Controller
 */

let activeCyclonesList = [];

async function loadCyclonePage() {
  if (!window.weatherMap.maps.cycloneTrackingMap) {
    window.weatherMap.initMap('cycloneTrackingMap', [18.0, 80.0], 4);
    window.weatherMap.addCycloneBasemaps('cycloneTrackingMap');
  }
  window.weatherMap.clearMap('cycloneTrackingMap');

  const container = document.getElementById('activeCyclonesContainer');
  const badge = document.getElementById('cycloneCountBadge');
  const select = document.getElementById('arrivalCycloneSelect');
  const mapStatus = document.getElementById('cycloneMapStatus');
  const updated = document.getElementById('lastUpdated');
  const feedsContainer = document.getElementById('officialBulletinsList');

  try {
    const res = await window.weatherApp.fetchAPI('/cyclones/active');
    activeCyclonesList = (res.cyclones || []).filter(c =>
      c.name && c.lat != null && c.lon != null &&
      Number.isFinite(Number(c.lat)) && Number.isFinite(Number(c.lon))
    );
    if (mapStatus) {
      const sourceNames = (res.sources_checked || []).join(', ') || 'No official feed responded';
      const checkedAt = res.checked_at ? window.weatherApp.formatDateTime(res.checked_at) : 'time unavailable';
      mapStatus.textContent = `LIVE OFFICIAL FEEDS · ${sourceNames} · checked ${checkedAt} · dashed paths are motion estimates, not official forecasts`;
    }
    if (updated && res.checked_at) updated.textContent = `Feed checked: ${window.weatherApp.formatDateTime(res.checked_at)}`;
    renderFeedStatus(feedsContainer, res);
    window.weatherMap.addCycloneBasemaps('cycloneTrackingMap');

    if (activeCyclonesList.length > 0) {
      if (badge) {
        badge.textContent = `${activeCyclonesList.length} Live System(s)`;
        badge.className = 'badge bg-danger';
      }
      renderActiveCyclones(container, activeCyclonesList);
      populateSelect(select, activeCyclonesList);
      plotCyclonesOnMap(activeCyclonesList);
      if (mapStatus) mapStatus.textContent = `${mapStatus.textContent} · spinning center = reported storm position`;
    } else {
      if (!res.sources_checked || !res.sources_checked.length) {
        throw new Error('No authoritative cyclone feed could be reached.');
      }
      if (badge) {
        badge.textContent = 'No active systems';
        badge.className = 'badge bg-success';
      }
      if (container) {
        container.innerHTML = `
          <div class="empty-state" style="padding:32px;">
            <div class="empty-state-icon">🌊</div>
            <div class="empty-state-title">No active tropical cyclones reported</div>
            <div class="empty-state-desc">${res.message || 'The responding official feeds report no active storms.'}</div>
            <div class="text-muted mt-2" style="font-size:11px;">This is a live-feed result, not a forecast. Recheck for updates.</div>
          </div>
        `;
      }
      if (select) select.innerHTML = '<option value="">No live cyclone available</option>';
      if (mapStatus) mapStatus.textContent = `LIVE FEEDS · ${res.message || 'No active cyclones reported'} · satellite / street map`;
    }
  } catch (err) {
    console.error('Error fetching cyclones:', err);
    activeCyclonesList = [];
    if (badge) {
      badge.textContent = 'Live status unavailable';
      badge.className = 'badge bg-warning text-dark';
    }
    if (container) {
      container.innerHTML = `
        <div class="alert alert-warning" role="status">
          Live cyclone status is unavailable: ${err.message}. No current storm status can be confirmed until an official feed responds.
        </div>
      `;
    }
    if (select) select.innerHTML = '<option value="">Live cyclone data unavailable</option>';
    if (mapStatus) mapStatus.textContent = `LIVE FEED UNAVAILABLE · ${err.message} · no storm position is being simulated`;
    if (feedsContainer) feedsContainer.textContent = `Official feed status unavailable: ${err.message}`;
  }
}

function renderFeedStatus(container, result) {
  if (!container) return;
  container.replaceChildren();
  const checked = Array.isArray(result.sources_checked) ? result.sources_checked : [];
  const unavailable = Array.isArray(result.sources_unavailable) ? result.sources_unavailable : [];
  const summary = document.createElement('p');
  summary.className = 'text-muted';
  summary.style.fontSize = '13px';
  summary.textContent = `${result.message || 'Feed check complete.'}${result.checked_at ? ` Last checked ${window.weatherApp.formatDateTime(result.checked_at)}.` : ''} Feed availability does not itself constitute an official warning bulletin.`;
  container.appendChild(summary);

  const list = document.createElement('ul');
  list.className = 'risk-text-list';
  checked.forEach(source => {
    const item = document.createElement('li');
    item.textContent = `${source}: responding`;
    list.appendChild(item);
  });
  unavailable.forEach(source => {
    const item = document.createElement('li');
    item.textContent = `${source}: unavailable`;
    list.appendChild(item);
  });
  if (checked.length || unavailable.length) container.appendChild(list);
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
          <strong>Max Wind:</strong> ${c.max_wind_speed == null ? 'Not reported' : `${c.max_wind_speed} km/h`}
        </div>
        <div style="font-size:12px; color:var(--color-text-muted);">
          Position: ${Number(c.lat).toFixed(2)}°, ${Number(c.lon).toFixed(2)}° &middot;
          Reported motion: ${c.movement_dir || 'Not reported'}${c.movement_speed == null ? '' : ` @ ${c.movement_speed} km/h`}
          &middot; ${c.source || 'Official feed'}
        </div>
      </div>
      <button class="btn btn-sm btn-outline-primary" onclick="focusCyclone(${Number(c.lat)}, ${Number(c.lon)})">
        Center Map
      </button>
    </div>
  `).join('');
}

function populateSelect(select, cyclones) {
  if (!select) return;
  select.innerHTML = '<option value="">Select a live cyclone</option>' + cyclones.map((c, index) => `
    <option value="${index}">${c.name} (${c.category || 'Active system'})</option>
  `).join('');
}

function plotCyclonesOnMap(cyclones) {
  cyclones.forEach(c => {
    window.weatherMap.addCycloneMarker('cycloneTrackingMap', c);
    window.weatherMap.addCycloneMovement('cycloneTrackingMap', c);
  });
  const movingSystems = cyclones.filter(c =>
    window.weatherMap.parseBearing(c.movement_dir) != null &&
    Number.isFinite(Number(c.movement_speed)) &&
    Number(c.movement_speed) > 0
  ).length;
  const mapStatus = document.getElementById('cycloneMapStatus');
  if (mapStatus && movingSystems < cyclones.length) {
    mapStatus.textContent += ` · motion vector available for ${movingSystems}/${cyclones.length} system(s)`;
  }
  if (cyclones.length === 1) {
    window.weatherMap.flyTo('cycloneTrackingMap', Number(cyclones[0].lat), Number(cyclones[0].lon), 6);
  } else if (cyclones.length > 1) {
    const bounds = L.latLngBounds(cyclones.map(c => [Number(c.lat), Number(c.lon)]));
    window.weatherMap.maps.cycloneTrackingMap.fitBounds(bounds.pad(0.35), { maxZoom: 6 });
  }
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
    calcBtn.addEventListener('click', async () => {
      const locationQuery = document.getElementById('arrivalCityInput').value.trim();
      const selectedValue = document.getElementById('arrivalCycloneSelect').value;
      const selectedIndex = selectedValue === '' ? -1 : Number(selectedValue);
      const cyclone = Number.isInteger(selectedIndex) && selectedIndex >= 0
        ? activeCyclonesList[selectedIndex]
        : null;
      const resBox = document.getElementById('arrivalResultsContainer');
      const title = document.getElementById('arrivalResultTitle');
      const distEl = document.getElementById('arrDistance');
      const dirEl = document.getElementById('arrDirection');
      const speedEl = document.getElementById('arrSpeed');
      const winEl = document.getElementById('arrWindow');

      if (!cyclone) {
        window.weatherApp.showToast('Select an active cyclone from the live official feeds first.', 'warning');
        return;
      }
      if (!locationQuery) {
        window.weatherApp.showToast('Enter a city and country to resolve its live coordinates.', 'warning');
        return;
      }

      calcBtn.disabled = true;
      try {
        const search = await window.weatherApp.fetchAPI(`/weather/search?q=${encodeURIComponent(locationQuery)}`);
        const locations = search.results && search.results.cities || [];
        if (!locations.length) throw new Error(`No location found for "${locationQuery}". Include the country name.`);
        const location = locations[0];
        const tLat = Number(location.lat);
        const tLon = Number(location.lon);
        if (!Number.isFinite(tLat) || !Number.isFinite(tLon)) {
          throw new Error('The location provider did not return valid coordinates.');
        }

        const lat1 = Number(cyclone.lat) * Math.PI / 180;
        const lat2 = tLat * Math.PI / 180;
        const deltaLat = lat2 - lat1;
        const deltaLon = (tLon - Number(cyclone.lon)) * Math.PI / 180;
        const a = Math.sin(deltaLat / 2) ** 2 +
          Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
        const distance = Math.round(6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
        const bearing = (Math.atan2(
          Math.sin(deltaLon) * Math.cos(lat2),
          Math.cos(lat1) * Math.sin(lat2) -
          Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLon)
        ) * 180 / Math.PI + 360) % 360;
        const reportedHeading = window.weatherMap.parseBearing(cyclone.movement_dir);
        const speed = Number(cyclone.movement_speed);

        title.textContent = `${location.name}${location.country_name ? `, ${location.country_name}` : ''} · ${cyclone.name}`;
        distEl.textContent = `${distance.toLocaleString()} km from reported storm center`;
        dirEl.textContent = cyclone.movement_dir
          ? `${cyclone.movement_dir} reported by ${cyclone.source || 'official feed'}`
          : 'Not reported by the official feed';
        speedEl.textContent = Number.isFinite(speed) && speed > 0
          ? `${speed} km/h reported translation speed`
          : 'Not reported by the official feed';

        if (reportedHeading == null || !Number.isFinite(speed) || speed <= 0) {
          winEl.textContent = 'Unavailable: feed has no movement vector';
        } else {
          const headingDifference = Math.abs(((bearing - reportedHeading + 540) % 360) - 180);
          winEl.textContent = headingDifference <= 45
            ? `About ${Math.round(distance / speed)} h at constant reported speed; not a forecast`
            : 'No estimate: location is not along the reported forward heading';
        }
        resBox.style.display = 'block';
      } catch (error) {
        window.weatherApp.showToast(`Could not check live location: ${error.message}`, 'danger');
      } finally {
        calcBtn.disabled = false;
      }
    });
  }

  window.setInterval(loadCyclonePage, 5 * 60 * 1000);
});
