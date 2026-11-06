"""
Weather API endpoints for current weather, forecasts, search, and history.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta

from Backend.services.weather_service import WeatherService
from Backend.models import City, WeatherObservation, HistoricalWeather

weather_bp = Blueprint('weather', __name__, url_prefix='/api/weather')
weather_service = WeatherService()


@weather_bp.route('/current', methods=['GET'])
def get_current():
    """
    Get current weather for a city or coordinates.
    Query params:
      - city: City name (e.g. "Indore")
      - lat, lon: Geographical coordinates
    """
    city = request.args.get('city')
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if city is not None:
        city = city.strip()
        if not city:
            return jsonify({'error': 'City parameter cannot be empty', 'status': 400}), 400
        data = weather_service.get_current_weather(city)
        status_code = data.get('status', 200) if isinstance(data, dict) else 200
        if 'error' in data:
            return jsonify(data), status_code
        return jsonify({'status': 'success', 'data': data}), 200

    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            return jsonify({'error': 'Latitude and longitude must be valid numbers', 'status': 400}), 400
        data = weather_service.get_weather_by_coords(lat_f, lon_f)
        status_code = data.get('status', 200) if isinstance(data, dict) else 200
        if 'error' in data:
            return jsonify(data), status_code
        return jsonify({'status': 'success', 'data': data}), 200

    return jsonify({'error': 'Either city or both lat and lon parameters are required', 'status': 400}), 400


@weather_bp.route('/forecast', methods=['GET'])
def get_forecast():
    """
    Get 5-day / 3-hour forecast for a city.
    Query params:
      - city: City name
      - days: Number of days (1-5, default 5)
    """
    city = request.args.get('city')
    if not city or not city.strip():
        return jsonify({'error': 'City parameter is required', 'status': 400}), 400

    days = request.args.get('days', 5)
    try:
        days = int(days)
    except ValueError:
        days = 5

    data = weather_service.get_forecast(city.strip(), days=days)
    status_code = data.get('status', 200) if isinstance(data, dict) else 200
    if 'error' in data:
        return jsonify(data), status_code
    return jsonify({'status': 'success', 'data': data}), 200


@weather_bp.route('/multiple', methods=['GET'])
def get_multiple():
    """
    Get current weather for multiple comma-separated cities.
    Query params:
      - cities: Comma-separated list (e.g. "Mumbai,Delhi,Indore")
    """
    cities_str = request.args.get('cities')
    if not cities_str or not cities_str.strip():
        return jsonify({'error': 'cities parameter is required', 'status': 400}), 400

    cities_list = [c.strip() for c in cities_str.split(',') if c.strip()]
    if not cities_list:
        return jsonify({'error': 'At least one valid city name is required', 'status': 400}), 400

    result = weather_service.get_multiple_cities_weather(cities_list)
    return jsonify({'status': 'success', 'data': result}), 200


@weather_bp.route('/search', methods=['GET'])
def search_city():
    """
    Search cities using geocoding API.
    Query params:
      - q: Search query (e.g. "Lon")
    """
    query = request.args.get('q')
    if not query or not query.strip():
        return jsonify({'error': 'Query parameter q is required', 'status': 400}), 400

    results = weather_service.search_city(query.strip())
    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), results.get('status', 400)
    return jsonify({'status': 'success', 'results': results}), 200


@weather_bp.route('/history', methods=['GET'])
def get_history():
    """
    Retrieve stored historical weather observations for a city.
    Query params:
      - city: City name
      - days: Number of past days to query (default 30)
    """
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'City parameter is required', 'status': 400}), 400

    days = request.args.get('days', 30)
    try:
        days = max(1, min(int(days), 90))
    except ValueError:
        days = 30

    city = City.query.filter(City.name.ilike(city_name.strip())).first()
    archive = weather_service.get_historical_archive(
        city.name if city else city_name.strip(),
        days=days
    )
    if 'error' in archive:
        if not city:
            return jsonify(archive), archive.get('status', 503)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        observations = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.desc(), WeatherObservation.id.desc())
            .all()
        )
        unique_records = {}
        for observation in observations:
            unique_records.setdefault(observation.observed_at, observation)
        if not unique_records:
            return jsonify(archive), archive.get('status', 503)
        records = [observation.to_dict() for observation in unique_records.values()]
        archive_warning = archive['error']
    else:
        records = archive['records']
        archive_warning = None

    return jsonify({
        'status': 'success',
        'city': archive.get('city', city.name if city else city_name.strip()),
        'country': archive.get('country', city.country if city else None),
        'days': days,
        'count': len(records),
        'records': records,
        'source': 'Open-Meteo archive (reanalysis)',
        'warning': archive_warning,
    }), 200
