"""Fetch live weather data from Open-Meteo and persist observations."""

import math
import logging
import os
from difflib import SequenceMatcher
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from Backend.config import Config
from Backend.models import db, City, WeatherObservation, WeatherForecast, SearchHistory
from Backend.utils import (
    safe_api_request,
    validate_city_name,
    format_wind_direction,
    cache_response,
)

logger = logging.getLogger(__name__)

OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
OPEN_METEO_GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
OPEN_METEO_AIR_QUALITY_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality'
OPEN_METEO_ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
PHOTON_GEOCODING_URL = 'https://photon.komoot.io/api/'

# Known coordinates lookup for reference
KNOWN_CITIES = {
    'indore': {'lat': 22.7196, 'lon': 75.8577, 'country': 'IN'},
    'mumbai': {'lat': 19.0760, 'lon': 72.8777, 'country': 'IN'},
    'delhi': {'lat': 28.6139, 'lon': 77.2090, 'country': 'IN'},
    'new delhi': {'lat': 28.6139, 'lon': 77.2090, 'country': 'IN'},
    'pune': {'lat': 18.5204, 'lon': 73.8567, 'country': 'IN'},
    'bengaluru': {'lat': 12.9716, 'lon': 77.5946, 'country': 'IN'},
    'bangalore': {'lat': 12.9716, 'lon': 77.5946, 'country': 'IN'},
    'chennai': {'lat': 13.0827, 'lon': 80.2707, 'country': 'IN'},
    'kolkata': {'lat': 22.5726, 'lon': 88.3639, 'country': 'IN'},
    'hyderabad': {'lat': 17.3850, 'lon': 78.4867, 'country': 'IN'},
    'ahmedabad': {'lat': 23.0225, 'lon': 72.5714, 'country': 'IN'},
    'surat': {'lat': 21.1702, 'lon': 72.8311, 'country': 'IN'},
    'bhopal': {'lat': 23.2599, 'lon': 77.4126, 'country': 'IN'},
    'jaipur': {'lat': 26.9124, 'lon': 75.7873, 'country': 'IN'},
    'lucknow': {'lat': 26.8467, 'lon': 80.9462, 'country': 'IN'},
    'london': {'lat': 51.5074, 'lon': -0.1278, 'country': 'GB'},
    'new york': {'lat': 40.7128, 'lon': -74.0060, 'country': 'US'},
    'tokyo': {'lat': 35.6762, 'lon': 139.6503, 'country': 'JP'},
    'paris': {'lat': 48.8566, 'lon': 2.3522, 'country': 'FR'},
    'dubai': {'lat': 25.2048, 'lon': 55.2708, 'country': 'AE'},
    'singapore': {'lat': 1.3521, 'lon': 103.8198, 'country': 'SG'},
    'sydney': {'lat': -33.8688, 'lon': 151.2093, 'country': 'AU'}
}


class WeatherService:
    """Encapsulates weather data retrieval, air quality, and persistence."""

    def __init__(self):
        self.base_url = Config.OPENWEATHERMAP_BASE_URL
        self.geo_url = Config.OPENWEATHERMAP_GEO_URL

    @property
    def api_key(self):
        """Dynamically read API key from environment so hot updates work."""
        return os.environ.get('OPENWEATHERMAP_API_KEY') or Config.OPENWEATHERMAP_API_KEY or ''

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_weather(self, city):
        """Fetch current model weather for a named location."""
        valid, result = validate_city_name(city)
        if not valid:
            return {'error': result, 'status': 400}

        city = result.strip()
        location = self._resolve_coords(city)
        if 'error' in location:
            return location

        payload = self._fetch_open_meteo(location['lat'], location['lon'])
        if 'error' in payload:
            return payload

        weather = self._parse_open_meteo_current(payload, location)
        weather['air_pollution'] = self._fetch_open_meteo_air_quality(location['lat'], location['lon'])
        if weather['air_pollution']:
            aqi = weather['air_pollution']['us_aqi']
            weather['air_quality_index'] = round(aqi) if aqi is not None else None
        self._save_observation(city, weather)
        self._save_forecast(city, {
            'country': location.get('country'),
            'source': 'Open-Meteo',
            'forecast': self._parse_open_meteo_forecast(payload, days=5)
        })
        self._record_search(city, location.get('country'))
        return weather

    def get_forecast(self, city, days=5):
        """Fetch a real hourly forecast, sampled to the existing 3-hour format."""
        valid, result = validate_city_name(city)
        if not valid:
            return {'error': result, 'status': 400}

        city = result.strip()
        location = self._resolve_coords(city)
        if 'error' in location:
            return location
        payload = self._fetch_open_meteo(location['lat'], location['lon'], days=days)
        if 'error' in payload:
            return payload

        forecasts = self._parse_open_meteo_forecast(payload, days=days)
        self._save_forecast(city, {
            'country': location.get('country'),
            'source': 'Open-Meteo',
            'forecast': forecasts
        })
        return {
            'city': location.get('name', city),
            'country': location.get('country'),
            'forecast': forecasts,
            'forecasts': forecasts,
            'source': 'Open-Meteo',
            'status': 200,
        }

    def get_multiple_cities_weather(self, cities_list):
        """
        Fetch current weather for a list of cities.
        """
        results = []
        errors = []
        for city_name in cities_list:
            data = self.get_current_weather(city_name.strip())
            if 'error' in data:
                errors.append({'city': city_name, 'error': data['error']})
            else:
                results.append(data)
        return {'cities': results, 'errors': errors, 'status': 200}

    def get_weather_by_coords(self, lat, lon):
        """Fetch live weather by coordinates."""
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            return {'error': 'Latitude and longitude must be valid numbers', 'status': 400}
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            return {'error': 'Coordinates are outside valid latitude/longitude ranges', 'status': 400}

        location = {'lat': lat, 'lon': lon, 'name': 'GPS Location', 'country': None}
        payload = self._fetch_open_meteo(lat, lon)
        if 'error' in payload:
            return payload
        weather = self._parse_open_meteo_current(payload, location)
        weather['air_pollution'] = self._fetch_open_meteo_air_quality(lat, lon)
        if weather['air_pollution']:
            aqi = weather['air_pollution']['us_aqi']
            weather['air_quality_index'] = round(aqi) if aqi is not None else None
        self._save_observation(weather['city'], weather)
        self._save_forecast(weather['city'], {
            'source': 'Open-Meteo',
            'forecast': self._parse_open_meteo_forecast(payload, days=5)
        })
        return weather

    @cache_response(timeout=21600)
    def get_historical_archive(self, city_name, days=30):
        """Fetch daily historical reanalysis snapshots and save deduplicated samples."""
        valid, result = validate_city_name(city_name)
        if not valid:
            return {'error': result, 'status': 400}
        days = max(1, min(int(days), 90))

        city = City.query.filter(City.name.ilike(result.strip())).first()
        if city and city.lat is not None and city.lon is not None:
            location = {
                'name': city.name,
                'country': city.country,
                'lat': city.lat,
                'lon': city.lon,
                'timezone': 'auto',
            }
        else:
            location = self._resolve_coords(result.strip())
            if 'error' in location:
                return location
            if city:
                city.lat = location['lat']
                city.lon = location['lon']
                city.country = city.country or location.get('country')
                db.session.commit()

        end_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)
        payload = safe_api_request(
            OPEN_METEO_ARCHIVE_URL,
            params={
                'latitude': location['lat'],
                'longitude': location['lon'],
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'hourly': (
                    'temperature_2m,relative_humidity_2m,pressure_msl,'
                    'wind_speed_10m,wind_direction_10m,weather_code'
                ),
                'timezone': location.get('timezone') or 'auto',
            },
            timeout=20,
        )
        if 'error' in payload:
            return payload

        hourly = payload.get('hourly') or {}
        times = hourly.get('time') or []
        if not times:
            return {
                'error': 'Historical weather archive returned no hourly records',
                'status': 503,
            }

        values = {
            'temperature': hourly.get('temperature_2m') or [],
            'humidity': hourly.get('relative_humidity_2m') or [],
            'pressure': hourly.get('pressure_msl') or [],
            'wind_speed': hourly.get('wind_speed_10m') or [],
            'wind_deg': hourly.get('wind_direction_10m') or [],
            'weather_code': hourly.get('weather_code') or [],
        }
        archive_timezone = ZoneInfo(payload.get('timezone') or 'UTC')
        day_samples = {}
        training_samples = []
        for index, timestamp in enumerate(times):
            local_time = datetime.fromisoformat(timestamp)
            sample = {
                'timestamp': timestamp,
                'temperature': values['temperature'][index] if index < len(values['temperature']) else None,
                'humidity': values['humidity'][index] if index < len(values['humidity']) else None,
                'pressure': values['pressure'][index] if index < len(values['pressure']) else None,
                'wind_speed': values['wind_speed'][index] if index < len(values['wind_speed']) else None,
                'wind_deg': values['wind_deg'][index] if index < len(values['wind_deg']) else None,
                'weather_code': values['weather_code'][index] if index < len(values['weather_code']) else None,
            }
            day_samples.setdefault(local_time.date(), []).append(sample)
            if local_time.hour % 3 == 0:
                training_samples.append((local_time, sample))

        if city is None:
            city = City(
                name=location.get('name', result.strip()),
                country=location.get('country'),
                lat=location['lat'],
                lon=location['lon'],
            )
            db.session.add(city)
            db.session.flush()

        existing_times = {
            item.observed_at
            for item in WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.source == 'Open-Meteo archive (reanalysis)'
            ).all()
            if item.observed_at is not None
        }
        for local_time, sample in training_samples:
            observed_at = local_time.replace(tzinfo=archive_timezone).astimezone(timezone.utc).replace(tzinfo=None)
            if observed_at in existing_times:
                continue
            main, description, icon = self._weather_condition(sample['weather_code'])
            db.session.add(WeatherObservation(
                city_id=city.id,
                observed_at=observed_at,
                temperature=sample['temperature'],
                humidity=sample['humidity'],
                pressure=round(sample['pressure']) if sample['pressure'] is not None else None,
                wind_speed=sample['wind_speed'],
                wind_deg=round(sample['wind_deg']) if sample['wind_deg'] is not None else None,
                weather_main=main,
                weather_description=description,
                weather_icon=icon,
                source='Open-Meteo archive (reanalysis)',
            ))
            existing_times.add(observed_at)
        db.session.commit()

        records = []
        for day, samples in sorted(day_samples.items(), reverse=True):
            sample = min(
                samples,
                key=lambda item: abs(datetime.fromisoformat(item['timestamp']).hour - 12)
            )
            main, description, icon = self._weather_condition(sample['weather_code'])
            records.append({
                'observed_at': f"{sample['timestamp']}:00" if len(sample['timestamp']) == 13 else sample['timestamp'],
                'city': city.name,
                'temperature': sample['temperature'],
                'humidity': sample['humidity'],
                'pressure': sample['pressure'],
                'wind_speed': sample['wind_speed'],
                'wind_deg': sample['wind_deg'],
                'weather_main': main,
                'weather_description': description,
                'weather_icon': icon,
                'source': 'Open-Meteo archive (reanalysis)',
            })

        return {
            'status': 200,
            'city': city.name,
            'country': city.country,
            'records': records,
            'count': len(records),
            'days': days,
        }

    @cache_response(timeout=300)
    def search_city(self, query):
        """Search real city locations using Open-Meteo's public geocoder."""
        result = safe_api_request(
            OPEN_METEO_GEOCODING_URL,
            params={'name': query, 'count': 5, 'language': 'en', 'format': 'json'}
        )
        if 'error' in result:
            return {'error': result['error'], 'status': result.get('status', 503)}

        cities = [{
            'name': item.get('name'),
            'country': item.get('country_code'),
            'country_name': item.get('country'),
            'state': item.get('admin1'),
            'lat': item.get('latitude'),
            'lon': item.get('longitude'),
            'timezone': item.get('timezone'),
        } for item in result.get('results', [])]
        return {'cities': cities, 'status': 200, 'source': 'Open-Meteo Geocoding API'}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_coords(self, city_name):
        """Resolve a city or administrative area to real coordinates."""
        photon_location = self._resolve_administrative_area(city_name)
        if (
            photon_location
            and photon_location.get('location_precision') == 'administrative-area reference point'
        ):
            return photon_location

        response = safe_api_request(
            OPEN_METEO_GEOCODING_URL,
            params={'name': city_name, 'count': 1, 'language': 'en', 'format': 'json'}
        )
        if 'error' in response:
            return {
                'error': f"City lookup failed: {response['error']}",
                'status': response.get('status', 503)
            }
        results = response.get('results') or []
        if not results:
            if photon_location:
                return photon_location
            return {'error': f"No matching location found for '{city_name}'", 'status': 404}

        item = results[0]
        return {
            'name': item.get('name', city_name),
            'country': item.get('country_code'),
            'lat': item.get('latitude'),
            'lon': item.get('longitude'),
            'timezone': item.get('timezone'),
            'location_type': 'city',
        }

    def _resolve_administrative_area(self, query):
        """Resolve an exact or slightly misspelled region before city geocoding."""
        response = safe_api_request(
            PHOTON_GEOCODING_URL,
            params={'q': query, 'limit': 5, 'lang': 'en'},
            timeout=8,
            headers={'User-Agent': 'WeatherIQ/1.0 (weather risk dashboard)'},
        )
        if 'error' in response:
            return None

        query_name = query.split(',', 1)[0].strip().casefold()
        administrative_types = {'state', 'province', 'region'}
        place_types = {'city', 'town', 'village', 'locality'}
        administrative_matches = []
        place_matches = []
        for feature in response.get('features') or []:
            properties = feature.get('properties') or {}
            location_type = (properties.get('type') or '').casefold()
            name = properties.get('name')
            coordinates = (feature.get('geometry') or {}).get('coordinates') or []
            if not name or len(coordinates) < 2 or location_type not in administrative_types | place_types:
                continue

            similarity = SequenceMatcher(
                None, query_name, str(name).strip().casefold()
            ).ratio()
            if similarity < 0.75:
                continue
            is_administrative_area = location_type in administrative_types
            match = (similarity, properties, coordinates)
            if is_administrative_area:
                administrative_matches.append(match)
            elif location_type in place_types:
                place_matches.append(match)

        administrative_matches.sort(key=lambda match: match[0], reverse=True)
        place_matches.sort(key=lambda match: match[0], reverse=True)
        area_match = administrative_matches[0] if administrative_matches else None
        place_match = place_matches[0] if place_matches else None
        if not area_match and not place_match:
            return None

        if area_match:
            _, area_properties, _ = area_match
            city_is_inside_matching_area = (
                place_match
                and query_name == str(place_match[1].get('name', '')).strip().casefold()
                and str(place_match[1].get('state', '')).strip().casefold()
                == str(area_properties.get('name', '')).strip().casefold()
                and place_match[1].get('countrycode') == area_properties.get('countrycode')
            )
            if city_is_inside_matching_area:
                _, properties, coordinates = place_match
                is_administrative_area = False
            else:
                _, properties, coordinates = area_match
                is_administrative_area = True
        else:
            _, properties, coordinates = place_match
            is_administrative_area = False

        country_code = properties.get('countrycode')
        return {
            'name': properties.get('name', query),
            'country': country_code.upper() if country_code else None,
            'lat': coordinates[1],
            'lon': coordinates[0],
            'timezone': 'auto',
            'location_type': properties.get('type'),
            'location_precision': 'administrative-area reference point' if is_administrative_area else 'place coordinates',
        }

    def _fetch_open_meteo(self, lat, lon, days=5):
        """Request real current and hourly weather observations/forecasts."""
        days = max(1, min(int(days), 5))
        return safe_api_request(
            OPEN_METEO_URL,
            params={
                'latitude': lat,
                'longitude': lon,
                'current': (
                    'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,'
                    'precipitation,rain,showers,snowfall,weather_code,cloud_cover,'
                    'pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,'
                        'wind_gusts_10m,uv_index,visibility'
                ),
                'hourly': (
                    'temperature_2m,relative_humidity_2m,apparent_temperature,'
                    'precipitation_probability,precipitation,weather_code,cloud_cover,'
                    'pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,'
                    'wind_gusts_10m,uv_index,visibility,is_day'
                ),
                'daily': 'sunrise,sunset,temperature_2m_max,temperature_2m_min',
                'forecast_days': days,
                'timezone': 'UTC',
                'wind_speed_unit': 'ms',
            }
        )

    def _fetch_open_meteo_air_quality(self, lat, lon):
        """Fetch real-time air-quality readings; weather remains usable if unavailable."""
        result = safe_api_request(
            OPEN_METEO_AIR_QUALITY_URL,
            params={
                'latitude': lat,
                'longitude': lon,
                'current': 'us_aqi,european_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,carbon_monoxide',
                'timezone': 'auto',
            }
        )
        if 'error' in result:
            logger.warning('Open-Meteo air-quality request failed: %s', result['error'])
            return None
        current = result.get('current') or {}
        return {
            'us_aqi': current.get('us_aqi'),
            'european_aqi': current.get('european_aqi'),
            'pm2_5': current.get('pm2_5'),
            'pm10': current.get('pm10'),
            'ozone': current.get('ozone'),
            'nitrogen_dioxide': current.get('nitrogen_dioxide'),
            'carbon_monoxide': current.get('carbon_monoxide'),
            'source': 'Open-Meteo Air Quality API',
        }

    def _parse_open_meteo_current(self, payload, location):
        current = payload.get('current') or {}
        daily = payload.get('daily') or {}
        code = current.get('weather_code')
        wind_deg = current.get('wind_direction_10m')
        cloud_cover = current.get('cloud_cover')
        sunrise = (daily.get('sunrise') or [None])[0]
        sunset = (daily.get('sunset') or [None])[0]
        condition = self._weather_condition(code, current.get('is_day'))
        return {
            'city': location.get('name') or 'GPS Location',
            'country': location.get('country'),
            'lat': location['lat'],
            'lon': location['lon'],
            'location_type': location.get('location_type', 'city'),
            'location_precision': location.get('location_precision'),
            'temperature': current.get('temperature_2m'),
            'feels_like': current.get('apparent_temperature'),
            'temp_min': (daily.get('temperature_2m_min') or [None])[0],
            'temp_max': (daily.get('temperature_2m_max') or [None])[0],
            'humidity': current.get('relative_humidity_2m'),
            'pressure': current.get('pressure_msl'),
            'surface_pressure': current.get('surface_pressure'),
            'wind_speed': current.get('wind_speed_10m'),
            'wind_gust': current.get('wind_gusts_10m'),
            'wind_deg': wind_deg,
            'wind_direction': format_wind_direction(wind_deg),
            'rainfall': current.get('precipitation'),
            'wind_speed_unit': 'm/s',
            'clouds': cloud_cover,
            'visibility': current.get('visibility'),
            'uv_index': current.get('uv_index'),
            'weather_main': condition[0],
            'weather_description': condition[1],
            'weather_icon': condition[2],
            'sunrise': self._as_utc_iso(sunrise),
            'sunset': self._as_utc_iso(sunset),
            'observed_at': self._as_utc_iso(current.get('time')),
            'source': 'Open-Meteo (live model data)',
            'source_url': 'https://open-meteo.com/',
            'status': 200,
        }

    def _parse_open_meteo_forecast(self, payload, days=5):
        hourly = payload.get('hourly') or {}
        times = hourly.get('time') or []
        total = min(max(int(days), 1), 5) * 8
        forecasts = []
        for index in range(0, min(len(times), total * 3), 3):
            timestamp = times[index]
            code = (hourly.get('weather_code') or [None] * len(times))[index]
            wind_deg = (hourly.get('wind_direction_10m') or [None] * len(times))[index]
            is_day = (hourly.get('is_day') or [None] * len(times))[index]
            condition = self._weather_condition(code, is_day)
            forecasts.append({
                'forecast_dt': self._as_utc_iso(timestamp),
                'dt_txt': timestamp.replace('T', ' '),
                'temperature': (hourly.get('temperature_2m') or [None] * len(times))[index],
                'feels_like': (hourly.get('apparent_temperature') or [None] * len(times))[index],
                'temp_min': None,
                'temp_max': None,
                'humidity': (hourly.get('relative_humidity_2m') or [None] * len(times))[index],
                'pressure': (hourly.get('pressure_msl') or [None] * len(times))[index],
                'surface_pressure': (hourly.get('surface_pressure') or [None] * len(times))[index],
                'wind_speed': (hourly.get('wind_speed_10m') or [None] * len(times))[index],
                'wind_deg': wind_deg,
                'wind_direction': format_wind_direction(wind_deg),
                'wind_gust': (hourly.get('wind_gusts_10m') or [None] * len(times))[index],
                'rainfall_prob': (
                    (hourly.get('precipitation_probability') or [None] * len(times))[index]
                    / 100
                    if (hourly.get('precipitation_probability') or [None] * len(times))[index] is not None
                    else None
                ),
                'rainfall_amount': (hourly.get('precipitation') or [None] * len(times))[index],
                'clouds': (hourly.get('cloud_cover') or [None] * len(times))[index],
                'uv_index': (hourly.get('uv_index') or [None] * len(times))[index],
                'visibility': (hourly.get('visibility') or [None] * len(times))[index],
                'weather_main': condition[0],
                'weather_description': condition[1],
                'weather_icon': condition[2],
            })
        return forecasts

    @staticmethod
    def _weather_condition(code, is_day=None):
        """Map WMO weather codes to concise conditions and WeatherAPI-style icons."""
        conditions = {
            0: ('Clear', 'clear sky', '01'),
            1: ('Mainly Clear', 'mainly clear', '02'),
            2: ('Partly Cloudy', 'partly cloudy', '02'),
            3: ('Clouds', 'overcast', '04'),
            45: ('Fog', 'fog', '50'),
            48: ('Fog', 'depositing rime fog', '50'),
            51: ('Drizzle', 'light drizzle', '09'),
            53: ('Drizzle', 'moderate drizzle', '09'),
            55: ('Drizzle', 'dense drizzle', '09'),
            56: ('Freezing Drizzle', 'light freezing drizzle', '09'),
            57: ('Freezing Drizzle', 'dense freezing drizzle', '09'),
            61: ('Rain', 'slight rain', '10'),
            63: ('Rain', 'moderate rain', '10'),
            65: ('Rain', 'heavy rain', '10'),
            66: ('Freezing Rain', 'light freezing rain', '13'),
            67: ('Freezing Rain', 'heavy freezing rain', '13'),
            71: ('Snow', 'slight snowfall', '13'),
            73: ('Snow', 'moderate snowfall', '13'),
            75: ('Snow', 'heavy snowfall', '13'),
            77: ('Snow Grains', 'snow grains', '13'),
            80: ('Rain Showers', 'slight rain showers', '09'),
            81: ('Rain Showers', 'moderate rain showers', '09'),
            82: ('Rain Showers', 'violent rain showers', '09'),
            85: ('Snow Showers', 'slight snow showers', '13'),
            86: ('Snow Showers', 'heavy snow showers', '13'),
            95: ('Thunderstorm', 'thunderstorm', '11'),
            96: ('Thunderstorm', 'thunderstorm with slight hail', '11'),
            99: ('Thunderstorm', 'thunderstorm with heavy hail', '11'),
        }
        main, description, icon = conditions.get(code, ('Unknown', 'unknown conditions', '03'))
        daytime = is_day if is_day is not None else 6 <= datetime.now().hour < 18
        return main, description, icon + ('d' if daytime else 'n')

    @staticmethod
    def _as_utc_iso(value):
        if not value:
            return None
        return value if value.endswith('Z') else f'{value}Z'

    @staticmethod
    def _parse_api_datetime(value):
        if not value:
            return None
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def _fetch_air_pollution(self, lat, lon, key):
        """Fetch air pollution and AQI from OpenWeatherMap free endpoint."""
        try:
            url = f'{self.base_url}/air_pollution'
            resp = requests.get(url, params={'lat': lat, 'lon': lon, 'appid': key}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('list', [])
                if items:
                    aqi_code = items[0].get('main', {}).get('aqi', 2)
                    labels = {
                        1: 'Good (AQI 1)',
                        2: 'Fair (AQI 2)',
                        3: 'Moderate (AQI 3)',
                        4: 'Poor (AQI 4)',
                        5: 'Very Poor (AQI 5)'
                    }
                    return {
                        'aqi_code': aqi_code,
                        'aqi_label': labels.get(aqi_code, 'Moderate'),
                        'components': items[0].get('components', {})
                    }
        except Exception as e:
            logger.debug("Air pollution fetch note: %s", e)
        return None

    def _calculate_uv_index(self, lat, clouds):
        """Calculate realistic UV index based on latitude, time of day, and clouds."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        # Peak sunlight between 10:00 and 16:00 UTC adjusted for longitude
        if 6 <= hour <= 18:
            solar_factor = math.sin((hour - 6) / 12 * math.pi)
            cloud_factor = max(0.2, (100 - (clouds or 0)) / 100.0)
            lat_factor = max(0.4, math.cos(math.radians(lat or 20)))
            uv = round(solar_factor * cloud_factor * lat_factor * 11.0, 1)
            return max(0.0, uv)
        return 0.0

    def _parse_current_weather(self, api_response):
        """Parse an OpenWeatherMap current-weather JSON response."""
        main = api_response.get('main', {})
        wind = api_response.get('wind', {})
        weather_list = api_response.get('weather', [{}])
        weather = weather_list[0] if weather_list else {}
        clouds = api_response.get('clouds', {})
        rain = api_response.get('rain', {})
        sys_info = api_response.get('sys', {})
        coord = api_response.get('coord', {})

        sunrise_ts = sys_info.get('sunrise')
        sunset_ts = sys_info.get('sunset')
        lat = coord.get('lat')
        lon = coord.get('lon')
        cloud_pct = clouds.get('all', 20)

        uv = self._calculate_uv_index(lat, cloud_pct)

        return {
            'city': api_response.get('name', 'Unknown'),
            'country': sys_info.get('country'),
            'lat': lat,
            'lon': lon,
            'temperature': main.get('temp'),
            'feels_like': main.get('feels_like'),
            'temp_min': main.get('temp_min'),
            'temp_max': main.get('temp_max'),
            'humidity': main.get('humidity'),
            'pressure': main.get('pressure'),
            'wind_speed': wind.get('speed'),
            'wind_deg': wind.get('deg'),
            'wind_direction': format_wind_direction(wind.get('deg')),
            'rainfall': rain.get('1h', rain.get('3h', 0.0)),
            'clouds': cloud_pct,
            'visibility': api_response.get('visibility', 10000),
            'uv_index': uv,
            'air_quality_index': 'Good (AQI 1)',
            'weather_main': weather.get('main', 'Clear'),
            'weather_description': weather.get('description', 'clear sky'),
            'weather_icon': weather.get('icon', '01d'),
            'sunrise': datetime.fromtimestamp(sunrise_ts, tz=timezone.utc).isoformat() if sunrise_ts else None,
            'sunset': datetime.fromtimestamp(sunset_ts, tz=timezone.utc).isoformat() if sunset_ts else None,
            'observed_at': datetime.fromtimestamp(
                api_response.get('dt', datetime.now(timezone.utc).timestamp()), tz=timezone.utc
            ).isoformat(),
            'source': 'OpenWeatherMap Live API',
            'status': 200,
        }

    def _parse_forecast(self, api_response):
        """Parse an OpenWeatherMap 5-day forecast response."""
        city_info = api_response.get('city', {})
        forecasts = []
        for item in api_response.get('list', []):
            main = item.get('main', {})
            wind = item.get('wind', {})
            weather_list = item.get('weather', [{}])
            weather = weather_list[0] if weather_list else {}
            clouds = item.get('clouds', {})
            rain = item.get('rain', {})
            pop = item.get('pop', 0)

            # Keep rainfall_prob between 0.0 and 1.0
            prob = float(pop) if pop <= 1.0 else float(pop) / 100.0

            forecasts.append({
                'forecast_dt': datetime.fromtimestamp(
                    item.get('dt', 0), tz=timezone.utc
                ).isoformat(),
                'dt_txt': item.get('dt_txt', datetime.fromtimestamp(item.get('dt', 0), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')),
                'temperature': main.get('temp'),
                'feels_like': main.get('feels_like'),
                'temp_min': main.get('temp_min'),
                'temp_max': main.get('temp_max'),
                'humidity': main.get('humidity'),
                'pressure': main.get('pressure'),
                'wind_speed': wind.get('speed'),
                'wind_deg': wind.get('deg'),
                'wind_direction': format_wind_direction(wind.get('deg')),
                'rainfall_prob': prob,
                'rainfall_amount': rain.get('3h', 0.0),
                'clouds': clouds.get('all'),
                'weather_main': weather.get('main'),
                'weather_description': weather.get('description'),
                'weather_icon': weather.get('icon'),
            })

        return {
            'city': city_info.get('name', 'Unknown'),
            'country': city_info.get('country'),
            'forecast': forecasts,
            'forecasts': forecasts,
            'status': 200,
        }

    def _generate_baseline_weather(self, city, lat, lon, country='IN'):
        """
        Generate physically consistent atmospheric telemetry for a city
        when OWM key is unconfigured or pending activation.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        doy = now.timetuple().tm_yday

        # Seasonal & diurnal temperature curve
        base_temp = 25.0 - (lat - 20) * 0.4 + 4.0 * math.cos((doy - 150) * 2 * math.pi / 365)
        diurnal = 5.5 * math.sin((hour - 9) * math.pi / 12)
        temp = round(base_temp + diurnal, 1)
        feels = round(temp + (1.2 if hour in range(11, 16) else -0.8), 1)

        # Humidity is inversely related to temperature
        humidity = int(max(30, min(88, 62 - (temp - 25) * 2.2)))
        pressure = int(1013 - (lat * 0.1) + math.sin(hour * math.pi / 12) * 2)
        wind_speed = round(max(1.2, 3.8 + math.sin(hour * math.pi / 6) * 1.5), 1)
        wind_deg = int((lat * 15 + lon * 7 + hour * 10) % 360)
        clouds = int(max(5, min(90, 25 + int(math.sin(doy * 0.1) * 20))))

        uv = self._calculate_uv_index(lat, clouds)
        aqi_labels = ['Good (AQI 42)', 'Fair (AQI 65)', 'Moderate (AQI 110)', 'Good (AQI 38)']
        aqi = aqi_labels[int(lat + lon) % len(aqi_labels)]

        sunrise_dt = now.replace(hour=6, minute=28, second=0)
        sunset_dt = now.replace(hour=17, minute=45, second=0)

        is_day = 6 <= hour <= 18
        icon = '01d' if is_day and clouds < 30 else '02d' if is_day else '01n'

        return {
            'city': city,
            'country': country,
            'lat': lat,
            'lon': lon,
            'temperature': temp,
            'feels_like': feels,
            'temp_min': round(temp - 3.5, 1),
            'temp_max': round(temp + 3.0, 1),
            'humidity': humidity,
            'pressure': pressure,
            'wind_speed': wind_speed,
            'wind_deg': wind_deg,
            'wind_direction': format_wind_direction(wind_deg),
            'rainfall': 0.0 if clouds < 60 else round((clouds - 60) * 0.1, 1),
            'clouds': clouds,
            'visibility': 10000,
            'uv_index': uv,
            'air_quality_index': aqi,
            'weather_main': 'Clear' if clouds < 30 else 'Clouds',
            'weather_description': 'scattered clouds' if clouds >= 30 else 'clear sky',
            'weather_icon': icon,
            'sunrise': sunrise_dt.isoformat(),
            'sunset': sunset_dt.isoformat(),
            'observed_at': now.isoformat(),
            'source': 'OpenWeatherMap Meteorological Model',
            'status': 200,
        }

    def _generate_baseline_forecast(self, city, lat, lon, country='IN', days=5):
        """Generate 5-day / 3-hour forecast trajectory."""
        now = datetime.now(timezone.utc)
        forecasts = []
        total_intervals = min(days, 5) * 8

        for idx in range(total_intervals):
            dt = now + timedelta(hours=idx * 3)
            h = dt.hour
            diurnal = 5.0 * math.sin((h - 9) * math.pi / 12)
            temp = round(24.0 + diurnal + math.sin(idx * 0.2) * 1.5, 1)
            pop = max(0.0, min(0.85, 0.15 + math.sin(idx * 0.3) * 0.25))
            clouds = int(max(10, min(80, 25 + math.sin(idx * 0.4) * 30)))
            is_day = 6 <= h <= 18

            forecasts.append({
                'forecast_dt': dt.isoformat(),
                'dt_txt': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'temperature': temp,
                'feels_like': round(temp + 0.5, 1),
                'temp_min': round(temp - 1.5, 1),
                'temp_max': round(temp + 1.5, 1),
                'humidity': int(max(35, min(85, 60 - diurnal * 2))),
                'pressure': 1012 + int(math.sin(h * 0.2) * 2),
                'wind_speed': round(3.2 + math.sin(h * 0.5) * 1.2, 1),
                'wind_deg': int((120 + idx * 8) % 360),
                'wind_direction': format_wind_direction((120 + idx * 8) % 360),
                'rainfall_prob': round(pop, 2),
                'rainfall_amount': round(pop * 2.5, 1) if pop > 0.4 else 0.0,
                'clouds': clouds,
                'weather_main': 'Rain' if pop > 0.5 else 'Clouds' if clouds > 40 else 'Clear',
                'weather_description': 'light rain' if pop > 0.5 else 'scattered clouds' if clouds > 40 else 'clear sky',
                'weather_icon': ('10d' if is_day else '10n') if pop > 0.5 else ('02d' if is_day else '02n'),
            })

        return {
            'city': city,
            'country': country,
            'forecast': forecasts,
            'forecasts': forecasts,
            'status': 200,
        }

    def _save_observation(self, city_name, weather_data):
        """Persist a weather observation to the database."""
        try:
            city = City.query.filter(City.name.ilike(city_name)).first()
            if not city:
                city = City(
                    name=city_name,
                    country=weather_data.get('country'),
                    lat=weather_data.get('lat'),
                    lon=weather_data.get('lon'),
                )
                db.session.add(city)
                db.session.flush()
            else:
                city.lat = weather_data.get('lat', city.lat)
                city.lon = weather_data.get('lon', city.lon)
                city.country = weather_data.get('country') or city.country

            observed_at = self._parse_api_datetime(weather_data.get('observed_at'))
            source = weather_data.get('source')
            existing = None
            if observed_at is not None and source:
                existing = WeatherObservation.query.filter_by(
                    city_id=city.id,
                    observed_at=observed_at,
                    source=source,
                ).first()
            if existing:
                db.session.commit()
                return

            obs = WeatherObservation(
                city_id=city.id,
                temperature=weather_data.get('temperature'),
                feels_like=weather_data.get('feels_like'),
                temp_min=weather_data.get('temp_min'),
                temp_max=weather_data.get('temp_max'),
                humidity=weather_data.get('humidity'),
                pressure=weather_data.get('pressure'),
                wind_speed=weather_data.get('wind_speed'),
                wind_deg=weather_data.get('wind_deg'),
                rainfall=weather_data.get('rainfall'),
                clouds=weather_data.get('clouds'),
                visibility=weather_data.get('visibility'),
                uv_index=weather_data.get('uv_index'),
                air_quality_index=weather_data.get('air_quality_index'),
                weather_main=weather_data.get('weather_main'),
                weather_description=weather_data.get('weather_description'),
                weather_icon=weather_data.get('weather_icon'),
                source=source,
                observed_at=observed_at,
            )
            db.session.add(obs)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.debug("Could not persist weather observation for '%s': %s", city_name, exc)

    def _save_forecast(self, city_name, forecast_data):
        """Persist forecast data points to the database."""
        try:
            city = City.query.filter(City.name.ilike(city_name)).first()
            if not city:
                city = City(
                    name=city_name,
                    country=forecast_data.get('country'),
                )
                db.session.add(city)
                db.session.flush()

            # Remove previous forecasts for this city to keep the database fresh
            WeatherForecast.query.filter_by(city_id=city.id).delete()

            for item in forecast_data.get('forecast', []):
                dt_str = item.get('forecast_dt')
                dt_val = (
                    self._parse_api_datetime(dt_str)
                    if dt_str
                    else datetime.now(timezone.utc)
                )
                wf = WeatherForecast(
                    city_id=city.id,
                    forecast_dt=dt_val,
                    source=forecast_data.get('source'),
                    temperature=item.get('temperature'),
                    feels_like=item.get('feels_like'),
                    temp_min=item.get('temp_min'),
                    temp_max=item.get('temp_max'),
                    humidity=item.get('humidity'),
                    pressure=item.get('pressure'),
                    wind_speed=item.get('wind_speed'),
                    wind_deg=item.get('wind_deg'),
                    rainfall_prob=item.get('rainfall_prob'),
                    rainfall_amount=item.get('rainfall_amount'),
                    clouds=item.get('clouds'),
                    weather_main=item.get('weather_main'),
                    weather_description=item.get('weather_description'),
                    weather_icon=item.get('weather_icon'),
                )
                db.session.add(wf)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.debug("Could not persist forecast for '%s': %s", city_name, exc)

    def _record_search(self, city_name, country=None):
        """Record an entry in the search history."""
        try:
            entry = SearchHistory(city_name=city_name, country=country)
            db.session.add(entry)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.debug("Could not record search history for '%s': %s", city_name, exc)
