# 🌦️ Advanced Weather Intelligence & Cyclone Monitoring System

A professional, full-stack weather intelligence platform built with Python Flask backend and modern JavaScript frontend. Features real-time weather monitoring, cyclone tracking, disaster risk assessment, machine learning predictions, and interactive data visualizations.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-red.svg)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [API Configuration](#api-configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Screenshots](#screenshots)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)

---

## 🌐 Overview

The Advanced Weather Intelligence & Cyclone Monitoring System is an enterprise-grade weather platform that provides:

- **Live weather and forecasts** from the public Open-Meteo weather and geocoding APIs (no API key required)
- **Cyclone tracking** using NOAA NHC, JTWC, and IMD data sources
- **Interactive maps** powered by Leaflet.js and public OpenStreetMap tiles
- **Light and dark themes** with persistent user preference
- **Data analytics** with Chart.js visualizations
- **Machine learning predictions** using scikit-learn
- **Disaster risk assessment** with multi-factor analysis
- **Alert management** with threshold-based notifications

This project demonstrates full-stack development skills including Python backend engineering, REST API design, database management, data science, interactive visualization, and responsive UI/UX design.

---

## ✨ Key Features

### 🌡️ Weather Dashboard
- Current weather conditions with 15+ parameters
- Live 24-hour temperature and five-day temperature/precipitation charts
- Data-flow diagram showing how live readings power dashboard visuals
- City search with autocomplete
- Browser geolocation support
- Multiple city comparison
- Favorite cities management
- Auto-refresh every 15 minutes

### 📊 Weather Analytics
- Historical observations and forecast trends for temperature, humidity, pressure, wind speed, and direction
- Rainfall prediction charts
- Multi-city comparison graphs
- Configurable time ranges (24h, 7d, 30d)
- Clear provider errors when live data cannot be reached (no fabricated fallback readings)

### 🌀 Cyclone Monitoring
- Real-time active cyclone tracking
- Official NHC formation outlooks and forecast tracks (Atlantic, Eastern Pacific, and Central Pacific)
- Interactive map with NASA GIBS/NOAA GOES infrared satellite layers and reported cyclone movement
- Open-Meteo wind, cloud, wave, sea-level-height, and sea-surface-temperature model samples at the storm position
- Estimated arrival calculator
- Historical cyclone database
- Official warnings from IMD/NOAA

### ⚠️ Disaster Risk Assessment
- Multi-factor risk scoring (0-100)
- Wind, rainfall, flood, and storm surge risk
- Risk level classification (Low to Extreme)
- Safety recommendations
- Methodology transparency

### 🤖 ML Weather Forecasting
- Temperature prediction models
- Rainfall trend analysis
- Anomaly detection
- Model evaluation metrics (MAE, RMSE, R²)
- Honest data sufficiency reporting

### 🔔 Alert System
- Threshold-based weather alerts
- Multi-severity classification
- Alert history and management
- Notification center

---

## 🛠️ Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Chart.js 4, Leaflet.js 1.9 |
| **Backend** | Python 3.10+, Flask 3.0, Flask-CORS, Flask-SQLAlchemy |
| **Database** | SQLite (dev), PostgreSQL-ready via SQLAlchemy ORM |
| **Data Science** | Pandas, NumPy, scikit-learn |
| **APIs** | Open-Meteo Weather, Marine, Geocoding & Air Quality; NOAA NHC; JTWC; IMD; NASA GIBS |
| **Mapping** | Leaflet.js with OpenStreetMap, Esri imagery, and NASA GIBS/NOAA GOES infrared layers |

---

## 🏗️ Architecture

```
weather-intelligence-system/
│
├── Backend/
│   ├── app.py                 # Flask application factory
│   ├── config/
│   │   └── __init__.py        # Configuration management
│   ├── routes/
│   │   ├── weather_routes.py  # Weather API endpoints
│   │   ├── cyclone_routes.py  # Cyclone monitoring endpoints
│   │   ├── analytics_routes.py # Analytics endpoints
│   │   ├── risk_routes.py     # Risk assessment endpoints
│   │   ├── alert_routes.py    # Alert management endpoints
│   │   └── settings_routes.py # User settings endpoints
│   ├── services/
│   │   ├── weather_service.py # Weather data processing
│   │   ├── cyclone_service.py # Cyclone data aggregation
│   │   ├── risk_service.py    # Risk assessment engine
│   │   └── alert_service.py   # Alert management
│   ├── models/
│   │   └── __init__.py        # SQLAlchemy ORM models
│   ├── database/
│   │   └── __init__.py        # Database initialization
│   ├── ml/
│   │   └── weather_predictor.py # ML prediction models
│   └── utils/
│       └── __init__.py        # Utility functions
│
├── Frontend/
│   ├── index.html             # Main dashboard
│   ├── pages/
│   │   ├── weather.html       # Live weather
│   │   ├── analytics.html     # Weather analytics
│   │   ├── cyclone.html       # Cyclone monitoring
│   │   ├── risk.html          # Disaster risk
│   │   ├── forecast.html      # ML forecasting
│   │   ├── historical.html    # Historical data
│   │   ├── alerts.html        # Alert center
│   │   └── settings.html      # Settings
│   ├── css/
│   │   └── styles.css         # Main stylesheet
│   ├── js/
│   │   ├── app.js             # Core application logic
│   │   ├── dashboard.js       # Dashboard module
│   │   ├── charts.js          # Chart utilities
│   │   ├── map.js             # Map utilities
│   │   ├── weather.js         # Weather page
│   │   ├── analytics.js       # Analytics page
│   │   ├── cyclone.js         # Cyclone page
│   │   ├── risk.js            # Risk page
│   │   ├── forecast.js        # Forecast page
│   │   ├── historical.js      # Historical page
│   │   ├── alerts.js          # Alerts page
│   │   └── settings.js        # Settings page
│   └── assets/
│       └── icons/             # Weather icons
│
├── data/                      # SQLite database storage
├── tests/                     # Backend tests
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Edge)
- Internet access for live public weather and cyclone feeds

### Step 1: Clone or Download
```bash
cd "c:\Users\kavis\OneDrive\Desktop\Documents\Desktop\Weather app"
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
copy .env.example .env
```
Edit `.env` to configure the Flask application:
```
FLASK_SECRET_KEY=any_random_string_for_sessions
FLASK_DEBUG=True
```

### Step 5: Initialize Database
The database is automatically created on first run.

---

## 🔑 API Configuration

### Weather and Air Quality (No key required)
- **Open-Meteo** provides current model conditions, hourly/5-day forecasts, city geocoding, and air-quality readings.
- The weather API returns errors rather than synthetic weather if the live provider cannot be reached.

### Data Sources (Automatic)
The following sources are accessed automatically (no API key needed):
- **NOAA NHC** — Active Atlantic and Eastern Pacific storm feeds
- **JTWC** — Active Northwest Pacific and North Indian Ocean warning bulletins
- **IMD** — India Meteorological Department cyclone feed (when available)

---

## 🚀 Running the Application

### Start the Backend Server
```bash
cd "c:\Users\kavis\OneDrive\Desktop\Documents\Desktop\Weather app"
venv\Scripts\activate
python run_weather_intelligence.py
```
The launcher starts the local server and opens the dashboard in your browser. Keep the terminal open while you use the app; press `Ctrl+C` to stop it.

On Windows, you can also double-click `START_WEATHER_INTELLIGENCE.bat` from the project folder.

### Access the Dashboard
The root local URL opens the Weather Intelligence dashboard directly:
```
http://127.0.0.1:5000/
```
`http://localhost:5000/` works too. These links only work on the computer running the server; another person cannot open your `localhost` link remotely.

### Deploy publicly on Vercel
The repository includes a Vercel Python function entry point and routing configuration. Before deploying:

1. Push this project to a GitHub repository. Do not upload `.env` or database files.
2. Create a hosted PostgreSQL database (for example, Neon or Vercel Postgres) and copy its connection URL.
3. Import the GitHub repository at [vercel.com/new](https://vercel.com/new).
4. In the Vercel project settings, add these environment variables for Production (and Preview if needed):
   - `DATABASE_URL` — the hosted PostgreSQL URL; `postgres://` and `postgresql://` URLs are supported.
   - `FLASK_SECRET_KEY` — a newly generated, private random value.
   - `FLASK_DEBUG` — `False`
5. Deploy. The project root and `/weather-intelligence.html` both serve the dashboard.

Vercel's filesystem is ephemeral. Without `DATABASE_URL`, the app uses a writable temporary SQLite database so the dashboard can start, but records are not persistent across serverless instances. Configure hosted PostgreSQL for persistent records. Never commit database credentials or secret keys.

---

## 📡 API Documentation

### Weather Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/api/weather/current` | Current weather | `city` or `lat`+`lon` |
| GET | `/api/weather/forecast` | 5-day forecast | `city`, `days` (optional) |
| GET | `/api/weather/multiple` | Multiple cities | `cities` (comma-separated) |
| GET | `/api/weather/search` | Search cities | `q` (query string) |
| GET | `/api/weather/history` | Historical data | `city`, `days` |
| GET | `/api/analytics/timeseries` | Saved observations and real forecast points for all chart metrics | `city`, `period` |

### Cyclone Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/api/cyclones/active` | Active cyclones | — |
| GET | `/api/cyclones/outlook` | NHC tropical cyclone formation chances and outlook areas | — |
| GET | `/api/cyclones/forecast` | Official NHC forecast track for an active NHC storm | `name` |
| GET | `/api/cyclones/environment` | Weather and marine model readings at a cyclone position | `lat`, `lon` |
| GET | `/api/cyclones/track/<id>` | Cyclone track | — |
| GET | `/api/cyclones/affected-regions/<id>` | Affected regions | — |
| GET | `/api/cyclones/arrival` | Arrival estimate | `cyclone_id`, `lat`, `lon` |

### Analytics Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/api/analytics/temperature` | Temperature data | `city`, `period` |
| GET | `/api/analytics/humidity` | Humidity data | `city`, `period` |
| GET | `/api/analytics/comparison` | City comparison | `cities` |
| GET | `/api/analytics/predictions` | ML predictions | `city`, `model` |

### Risk & Alert Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/api/risk/assessment` | Risk assessment | `city` |
| GET | `/api/alerts` | Active alerts | `city` (optional) |
| POST | `/api/alerts/read/<id>` | Mark alert read | — |
| GET | `/api/health` | Health check | — |

### Example Response: Current Weather
```json
{
  "status": "success",
  "data": {
    "city": "Indore",
    "country": "IN",
    "temperature": 32.5,
    "feels_like": 35.1,
    "temp_min": 30.2,
    "temp_max": 34.8,
    "humidity": 65,
    "pressure": 1012,
    "wind_speed": 3.5,
    "wind_direction": "SW",
    "clouds": 40,
    "visibility": 10000,
    "weather_main": "Clouds",
    "weather_description": "scattered clouds",
    "sunrise": "2024-01-15T06:45:00",
    "sunset": "2024-01-15T17:55:00",
    "observed_at": "2024-01-15T14:30:00"
  }
}
```

---

## 🗄️ Database Schema

The application uses SQLAlchemy ORM with the following models:

- **City** — Location information with favorites support
- **WeatherObservation** — Current weather snapshots
- **WeatherForecast** — Forecast data points
- **Cyclone** — Active and historical cyclone records
- **CycloneTrackPoint** — Cyclone trajectory coordinates
- **WeatherAlert** — Weather warnings and advisories
- **SearchHistory** — User search tracking
- **HistoricalWeather** — Aggregated historical data

The database is designed with SQLAlchemy ORM, making it portable from SQLite to PostgreSQL with a simple connection string change.

---

## 📸 Screenshots

> Screenshots will be added after the application is running.

| View | Description |
|------|-------------|
| Dashboard | Main overview with weather cards and charts |
| Weather | Detailed current conditions and forecast |
| Analytics | Interactive weather trend charts |
| Cyclone Map | Live cyclone tracking with Leaflet |
| Risk Assessment | Multi-factor disaster risk analysis |
| Alerts | Notification center with warnings |

---

## ⚠️ Known Limitations

1. **Live feed availability**: public weather and cyclone feeds may be temporarily unavailable; endpoints report errors instead of claiming fabricated data is live
2. **Cyclone Data**: Active-system data depends on official feed availability. NHC formation outlooks cover the Atlantic and eastern/central Pacific, not every global basin; forecast tracks are shown only when the NHC publishes one. Open-Meteo ocean and weather values are model outputs, not buoy/tide-gauge observations, and GOES imagery is near-real-time only where satellite coverage exists.
3. **ML Predictions**: Require sufficient historical data (50+ observations) for reliable predictions
4. **Historical Data**: Limited to data collected by the application; no pre-loaded historical dataset
5. **Offline Mode**: Application requires internet connectivity for API data
6. **Browser Notifications**: Not yet implemented (architecture is ready for integration)
7. **Email Alerts**: Not yet implemented (architecture is ready for integration)

---

## 🔮 Future Improvements

- [ ] PostgreSQL integration for production deployment
- [ ] User authentication and multi-user support
- [ ] Email notification integration (SMTP)
- [ ] Browser push notifications
- [ ] PWA (Progressive Web App) support
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Advanced ML models (LSTM, Prophet)
- [ ] Satellite imagery integration
- [ ] Weather radar overlay on maps
- [ ] Multi-language support
- [ ] REST API rate limiting with Flask-Limiter
- [ ] API documentation with Swagger/OpenAPI
- [ ] WebSocket for real-time updates

---

## 📄 License

This project is built for portfolio and educational purposes.

---

## 👨‍💻 Developer

Built as a comprehensive full-stack weather intelligence platform demonstrating:
- Python backend development
- REST API design and integration
- Database management with ORM
- Data analytics and visualization
- Machine learning applications
- Geospatial mapping
- Enterprise UI/UX design
- Software architecture best practices
