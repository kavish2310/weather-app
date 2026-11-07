/**
 * WeatherIQ - Geospatial Mapping Utilities powered by Leaflet.js
 */

class WeatherMap {
  constructor() {
    this.maps = {};
    this.layerGroups = {};
    this.baseLayers = {};
    this.layerControls = {};
    this.tileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    this.attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  }

  initMap(containerId, center = [20.5937, 78.9629], zoom = 5) {
    if (this.maps[containerId]) {
      this.maps[containerId].remove();
      delete this.maps[containerId];
    }

    const container = document.getElementById(containerId);
    if (!container) return null;

    const map = L.map(containerId, {
      center: center,
      zoom: zoom,
      zoomControl: true,
      scrollWheelZoom: true
    });

    const baseLayer = L.tileLayer(this.tileUrl, {
      attribution: this.attribution,
      maxZoom: 19
    }).addTo(map);

    this.maps[containerId] = map;
    this.baseLayers[containerId] = baseLayer;
    this.layerGroups[containerId] = L.layerGroup().addTo(map);

    // Invalidate size once rendered
    setTimeout(() => map.invalidateSize(), 300);
    return map;
  }

  addCycloneBasemaps(containerId) {
    const map = this.maps[containerId];
    if (!map || this.layerControls[containerId]) return;

    const street = this.baseLayers[containerId];
    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics',
        maxZoom: 18
      }
    );
    const goesEastInfrared = L.tileLayer(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GOES-East_ABI_Band13_Clean_Infrared/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      {
        attribution: 'Satellite imagery &copy; NASA GIBS / NOAA GOES-East',
        crossOrigin: true,
        maxNativeZoom: 6,
        maxZoom: 18,
        opacity: 0.72
      }
    );
    const goesWestInfrared = L.tileLayer(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/GOES-West_ABI_Band13_Clean_Infrared/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
      {
        attribution: 'Satellite imagery &copy; NASA GIBS / NOAA GOES-West',
        crossOrigin: true,
        maxNativeZoom: 6,
        maxZoom: 18,
        opacity: 0.72
      }
    );
    if (street && !map.hasLayer(street)) street.addTo(map);
    if (map.hasLayer(satellite)) map.removeLayer(satellite);
    this.layerControls[containerId] = L.control.layers(
      { 'Plain street map (default)': street, 'Satellite imagery': satellite },
      {
        'Optional: GOES-East infrared cloud image': goesEastInfrared,
        'Optional: GOES-West infrared cloud image': goesWestInfrared
      },
      { collapsed: true, position: 'topright' }
    ).addTo(map);
    this.layerControls[containerId].getContainer().querySelector(
      '.leaflet-control-layers-toggle'
    ).setAttribute('aria-label', 'Open map options');
  }

  clearMap(containerId) {
    if (this.layerGroups[containerId]) {
      this.layerGroups[containerId].clearLayers();
    }
  }

  addWeatherMarker(containerId, lat, lon, title, temp, condition, icon = '🌤️') {
    const lg = this.layerGroups[containerId];
    if (!lg) return;

    const customIcon = L.divIcon({
      className: 'custom-map-marker',
      html: `
        <div style="background: rgba(10, 22, 40, 0.9); border: 1px solid #2563eb; border-radius: 8px; padding: 4px 8px; color: #fff; font-family: Inter, sans-serif; font-size: 11px; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 4px;">
          <span>${icon}</span>
          <span style="font-weight: 600;">${title}: ${temp}</span>
        </div>
      `,
      iconSize: [110, 30],
      iconAnchor: [55, 15]
    });

    const marker = L.marker([lat, lon], { icon: customIcon });
    marker.bindPopup(`
      <div style="font-family: Inter, sans-serif; color: #0f172a; padding: 4px;">
        <h6 style="margin: 0 0 4px 0; font-weight: 700;">${title}</h6>
        <div>Condition: ${condition}</div>
        <div>Temperature: ${temp}</div>
      </div>
    `);
    lg.addLayer(marker);
  }

  addCycloneMarker(containerId, cyclone) {
    const lg = this.layerGroups[containerId];
    if (!lg || cyclone.lat == null || cyclone.lon == null ||
        !Number.isFinite(Number(cyclone.lat)) || !Number.isFinite(Number(cyclone.lon))) return;

    const cycloneIcon = L.divIcon({
      className: 'cyclone-marker-icon',
      html: `
        <div class="cyclone-marker-core">
          <span class="cyclone-marker-vortex" aria-hidden="true">🌀</span>
        </div>
      `,
      iconSize: [60, 60],
      iconAnchor: [30, 30]
    });

    const marker = L.marker([cyclone.lat, cyclone.lon], { icon: cycloneIcon });
    marker.bindPopup(`
      <div style="font-family: Inter, sans-serif; color: #0f172a; min-width: 180px;">
        <h5 style="margin: 0 0 6px 0; color: #b91c1c; font-weight: 700;">🌀 ${cyclone.name || 'Cyclone'}</h5>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Category:</strong> ${cyclone.category || 'N/A'}</div>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Wind Speed:</strong> ${cyclone.max_wind_speed ? cyclone.max_wind_speed + ' km/h' : 'N/A'}</div>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Movement:</strong> ${cyclone.movement_dir || 'N/A'} @ ${cyclone.movement_speed ? cyclone.movement_speed + ' km/h' : 'N/A'}</div>
        <div style="font-size: 12px;"><strong>Source:</strong> ${cyclone.source || 'Meteorological Service'}</div>
        <div style="font-size: 11px; color: #64748b;"><strong>Live position:</strong> ${Number(cyclone.lat).toFixed(2)}, ${Number(cyclone.lon).toFixed(2)}</div>
      </div>
    `);
    lg.addLayer(marker);
  }

  addCycloneMovement(containerId, cyclone, horizonHours = 6) {
    const lg = this.layerGroups[containerId];
    const map = this.maps[containerId];
    if (cyclone.lat == null || cyclone.lon == null) return false;
    const lat = Number(cyclone.lat);
    const lon = Number(cyclone.lon);
    const speed = Number(cyclone.movement_speed);
    const bearing = this.parseBearing(cyclone.movement_dir);
    if (!lg || !map || !Number.isFinite(lat) || !Number.isFinite(lon) ||
        !Number.isFinite(speed) || speed <= 0 || bearing == null) return false;

    const points = [];
    for (let hour = 0; hour <= horizonHours; hour += 1) {
      points.push(this.destinationPoint(lat, lon, bearing, speed * hour));
    }

    const motionPath = L.polyline(points, {
      color: '#f97316',
      weight: 4,
      opacity: 0.9,
      dashArray: '9 10',
      className: 'cyclone-motion-line'
    });
    motionPath.bindTooltip(
      `${horizonHours}-hour motion projection from provider-reported heading and speed · not an official forecast`,
      { sticky: true }
    );
    lg.addLayer(motionPath);

    const projectedPosition = points[points.length - 1];
    const projectedMarker = L.circleMarker(projectedPosition, {
      radius: 6,
      color: '#fff',
      weight: 2,
      fillColor: '#f97316',
      fillOpacity: 1
    });
    projectedMarker.bindTooltip(`${horizonHours}-hour motion projection (estimated)`);
    lg.addLayer(projectedMarker);
    return true;
  }

  parseBearing(direction) {
    if (direction == null) return null;
    const value = String(direction).trim().toUpperCase();
    const numeric = Number.parseFloat(value);
    if (Number.isFinite(numeric)) return ((numeric % 360) + 360) % 360;
    const bearings = {
      N: 0, NNE: 22.5, NE: 45, ENE: 67.5,
      E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
      S: 180, SSW: 202.5, SW: 225, WSW: 247.5,
      W: 270, WNW: 292.5, NW: 315, NNW: 337.5
    };
    return Object.prototype.hasOwnProperty.call(bearings, value) ? bearings[value] : null;
  }

  destinationPoint(latitude, longitude, bearing, distanceKm) {
    const earthRadiusKm = 6371;
    const angularDistance = distanceKm / earthRadiusKm;
    const bearingRadians = bearing * Math.PI / 180;
    const latitudeRadians = latitude * Math.PI / 180;
    const longitudeRadians = longitude * Math.PI / 180;
    const destinationLatitude = Math.asin(
      Math.sin(latitudeRadians) * Math.cos(angularDistance) +
      Math.cos(latitudeRadians) * Math.sin(angularDistance) * Math.cos(bearingRadians)
    );
    const destinationLongitude = longitudeRadians + Math.atan2(
      Math.sin(bearingRadians) * Math.sin(angularDistance) * Math.cos(latitudeRadians),
      Math.cos(angularDistance) - Math.sin(latitudeRadians) * Math.sin(destinationLatitude)
    );
    const wrappedLongitude = (destinationLongitude * 180 / Math.PI + 540) % 360 - 180;
    return [destinationLatitude * 180 / Math.PI, wrappedLongitude];
  }

  drawTrack(containerId, points, isForecast = false) {
    const lg = this.layerGroups[containerId];
    if (!lg || !points || points.length < 2) return;

    const latlngs = points.map(p => [p.lat, p.lon]);
    const polyline = L.polyline(latlngs, {
      color: isForecast ? '#f59e0b' : '#3b82f6',
      weight: 3,
      opacity: 0.85,
      dashArray: isForecast ? '6, 8' : null
    });

    polyline.bindTooltip(isForecast ? 'Forecast Trajectory' : 'Observed Path', { sticky: true });
    lg.addLayer(polyline);
  }

  flyTo(containerId, lat, lon, zoom = 8) {
    if (this.maps[containerId]) {
      this.maps[containerId].flyTo([lat, lon], zoom, { duration: 1.2 });
    }
  }
}

window.weatherMap = new WeatherMap();
