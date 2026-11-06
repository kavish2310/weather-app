"""
Analytics and Trends API endpoints for time-series weather data and ML predictions.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta

from Backend.models import City, WeatherObservation, WeatherForecast
from Backend.services.weather_service import WeatherService
from Backend.ml.weather_predictor import WeatherPredictor

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')
weather_service = WeatherService()
predictor = WeatherPredictor()


def _get_time_cutoff(period):
    """Determine datetime cutoff based on period string."""
    now = datetime.now(timezone.utc)
    if period == '24h':
        return now - timedelta(hours=24)
    elif period == '7d':
        return now - timedelta(days=7)
    elif period == '30d':
        return now - timedelta(days=30)
    return now - timedelta(days=7)


@analytics_bp.route('/timeseries', methods=['GET'])
def get_timeseries_analytics():
    """Return all persisted observations and forecasts for charting."""
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    period = request.args.get('period', '7d')
    cutoff = _get_time_cutoff(period)
    now = datetime.now(timezone.utc)
    horizon_days = {'24h': 1, '7d': 7, '30d': 30}.get(period, 7)
    forecast_end = now + timedelta(days=horizon_days)
    city = City.query.filter(City.name.ilike(city_name.strip())).first()

    if not city:
        live_weather = weather_service.get_current_weather(city_name.strip())
        if 'error' in live_weather:
            return jsonify(live_weather), live_weather.get('status', 503)
        city = City.query.filter(City.name.ilike(city_name.strip())).first()

    observations = []
    forecasts = []
    if city:
        observations = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.asc(), WeatherObservation.id.asc())
            .all()
        )
        observations = list({
            item.observed_at: item for item in observations
        }.values())
        forecasts = (
            WeatherForecast.query.filter(
                WeatherForecast.city_id == city.id,
                WeatherForecast.forecast_dt >= now,
                WeatherForecast.forecast_dt <= forecast_end,
                WeatherForecast.source == 'Open-Meteo'
            )
            .order_by(WeatherForecast.forecast_dt.asc())
            .all()
        )

        if not forecasts:
            weather_service.get_current_weather(city.name)
            forecasts = (
                WeatherForecast.query.filter(
                    WeatherForecast.city_id == city.id,
                    WeatherForecast.forecast_dt >= now,
                    WeatherForecast.forecast_dt <= forecast_end,
                    WeatherForecast.source == 'Open-Meteo'
                )
                .order_by(WeatherForecast.forecast_dt.asc())
                .all()
            )

    return jsonify({
        'status': 'success',
        'city': city.name if city else city_name.strip(),
        'period': period,
        'observations': [{
            'timestamp': (item.observed_at or item.created_at).isoformat(),
            'temperature': item.temperature,
            'feels_like': item.feels_like,
            'humidity': item.humidity,
            'pressure': item.pressure,
            'wind_speed': item.wind_speed,
            'wind_deg': item.wind_deg,
            'source': item.source
        } for item in observations],
        'forecasts': [{
            'timestamp': item.forecast_dt.isoformat(),
            'temperature': item.temperature,
            'feels_like': item.feels_like,
            'humidity': item.humidity,
            'pressure': item.pressure,
            'wind_speed': item.wind_speed,
            'wind_deg': item.wind_deg,
            'source': item.source
        } for item in forecasts]
    }), 200


@analytics_bp.route('/temperature', methods=['GET'])
def get_temperature_analytics():
    """Get temperature trends over a given period."""
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    period = request.args.get('period', '7d')
    city = City.query.filter(City.name.ilike(city_name.strip())).first()

    data_points = []
    if city:
        cutoff = _get_time_cutoff(period)
        obs = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.asc())
            .all()
        )
        for o in obs:
            data_points.append({
                'timestamp': (o.observed_at or o.created_at).isoformat(),
                'temperature': o.temperature,
                'feels_like': o.feels_like,
                'temp_min': o.temp_min,
                'temp_max': o.temp_max
            })

    # If local observations are few, supplement with 5-day forecast
    forecast_data = []
    f_res = weather_service.get_forecast(city_name.strip())
    if isinstance(f_res, dict) and 'forecast' in f_res:
        for item in f_res.get('forecast', []):
            forecast_data.append({
                'timestamp': item.get('dt_txt'),
                'temperature': item.get('temperature'),
                'feels_like': item.get('feels_like')
            })

    return jsonify({
        'status': 'success',
        'city': city_name,
        'period': period,
        'historical_points': data_points,
        'forecast_points': forecast_data
    }), 200


@analytics_bp.route('/humidity', methods=['GET'])
def get_humidity_analytics():
    """Get humidity trends over a given period."""
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    period = request.args.get('period', '7d')
    city = City.query.filter(City.name.ilike(city_name.strip())).first()

    data_points = []
    if city:
        cutoff = _get_time_cutoff(period)
        obs = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.asc())
            .all()
        )
        for o in obs:
            data_points.append({
                'timestamp': (o.observed_at or o.created_at).isoformat(),
                'humidity': o.humidity
            })

    return jsonify({
        'status': 'success',
        'city': city_name,
        'period': period,
        'points': data_points
    }), 200


@analytics_bp.route('/pressure', methods=['GET'])
def get_pressure_analytics():
    """Get atmospheric pressure trends."""
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    period = request.args.get('period', '7d')
    city = City.query.filter(City.name.ilike(city_name.strip())).first()

    data_points = []
    if city:
        cutoff = _get_time_cutoff(period)
        obs = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.asc())
            .all()
        )
        for o in obs:
            data_points.append({
                'timestamp': (o.observed_at or o.created_at).isoformat(),
                'pressure': o.pressure
            })

    return jsonify({
        'status': 'success',
        'city': city_name,
        'period': period,
        'points': data_points
    }), 200


@analytics_bp.route('/wind', methods=['GET'])
def get_wind_analytics():
    """Get wind speed and direction trends."""
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    period = request.args.get('period', '7d')
    city = City.query.filter(City.name.ilike(city_name.strip())).first()

    data_points = []
    if city:
        cutoff = _get_time_cutoff(period)
        obs = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.observed_at >= cutoff,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ])
            )
            .order_by(WeatherObservation.observed_at.asc())
            .all()
        )
        for o in obs:
            data_points.append({
                'timestamp': (o.observed_at or o.created_at).isoformat(),
                'wind_speed': o.wind_speed,
                'wind_deg': o.wind_deg
            })

    return jsonify({
        'status': 'success',
        'city': city_name,
        'period': period,
        'points': data_points
    }), 200


@analytics_bp.route('/comparison', methods=['GET'])
def compare_cities():
    """
    Compare current weather metrics across multiple cities.
    Query param: cities (comma separated)
    """
    cities_str = request.args.get('cities', '')
    if not cities_str.strip():
        return jsonify({'error': 'cities parameter is required', 'status': 400}), 400

    cities = [c.strip() for c in cities_str.split(',') if c.strip()]
    res = weather_service.get_multiple_cities_weather(cities)
    return jsonify(res), 200


@analytics_bp.route('/predictions', methods=['GET'])
def get_predictions():
    """
    Get ML predictions and model evaluation metrics for a city.
    Query params:
      - city: City name
      - model: Model type ('temperature', 'anomalies')
    """
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    model_type = request.args.get('model', 'temperature')

    if model_type == 'anomalies':
        res = predictor.detect_anomalies(city_name.strip())
    else:
        hours = request.args.get('hours', 24)
        try:
            hours = int(hours)
        except ValueError:
            hours = 24
        res = predictor.predict_temperature(city_name.strip(), hours_ahead=hours)

    if res.get('sufficient_data') is False:
        archive = weather_service.get_historical_archive(city_name.strip(), days=30)
        if 'error' not in archive:
            if model_type == 'anomalies':
                res = predictor.detect_anomalies(city_name.strip())
            else:
                res = predictor.predict_temperature(city_name.strip(), hours_ahead=hours)
        else:
            res['archive_notice'] = (
                'Live historical reanalysis could not be loaded: '
                f"{archive['error']}"
            )

    return jsonify(res), 200
