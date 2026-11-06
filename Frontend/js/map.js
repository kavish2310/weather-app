/**
 * WeatherIQ - Geospatial Mapping Utilities powered by Leaflet.js
 */

class WeatherMap {
  constructor() {
    this.maps = {};
    this.layerGroups = {};
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

    L.tileLayer(this.tileUrl, {
      attribution: this.attribution,
      maxZoom: 19
    }).addTo(map);

    this.maps[containerId] = map;
    this.layerGroups[containerId] = L.layerGroup().addTo(map);

    // Invalidate size once rendered
    setTimeout(() => map.invalidateSize(), 300);
    return map;
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
    if (!lg || !cyclone.lat || !cyclone.lon) return;

    const cycloneIcon = L.divIcon({
      className: 'cyclone-marker-icon',
      html: `
        <div style="width: 32px; height: 32px; background: rgba(239, 68, 68, 0.3); border: 2px solid #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; animation: pulse-danger 2s infinite;">
          🌀
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    const marker = L.marker([cyclone.lat, cyclone.lon], { icon: cycloneIcon });
    marker.bindPopup(`
      <div style="font-family: Inter, sans-serif; color: #0f172a; min-width: 180px;">
        <h5 style="margin: 0 0 6px 0; color: #b91c1c; font-weight: 700;">🌀 ${cyclone.name || 'Cyclone'}</h5>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Category:</strong> ${cyclone.category || 'N/A'}</div>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Wind Speed:</strong> ${cyclone.max_wind_speed ? cyclone.max_wind_speed + ' km/h' : 'N/A'}</div>
        <div style="font-size: 12px; margin-bottom: 3px;"><strong>Movement:</strong> ${cyclone.movement_dir || 'N/A'} @ ${cyclone.movement_speed ? cyclone.movement_speed + ' km/h' : 'N/A'}</div>
        <div style="font-size: 12px;"><strong>Source:</strong> ${cyclone.source || 'Meteorological Service'}</div>
      </div>
    `);
    lg.addLayer(marker);

    // Draw affected buffer circle (e.g. 250 km radius)
    const circle = L.circle([cyclone.lat, cyclone.lon], {
      color: '#ef4444',
      fillColor: '#ef4444',
      fillOpacity: 0.15,
      radius: 250000 // 250 km
    });
    circle.bindTooltip(`Gale warning radius: 250 km`, { sticky: true });
    lg.addLayer(circle);
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
