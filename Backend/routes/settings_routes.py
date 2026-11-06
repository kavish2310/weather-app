"""
Settings, Favorites, and Search History API endpoints.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone

from Backend.models import db, City, SearchHistory
from Backend.config import Config

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


@settings_bp.route('/favorites', methods=['GET'])
def get_favorites():
    """Get all favorite cities."""
    favorites = City.query.filter_by(is_favorite=True).all()
    return jsonify({
        'status': 'success',
        'count': len(favorites),
        'favorites': [f.to_dict() for f in favorites]
    }), 200


@settings_bp.route('/favorites', methods=['POST'])
def add_favorite():
    """
    Mark a city as favorite or create and mark.
    Body: {"city": "Indore", "country": "IN", "lat": 22.7, "lon": 75.8}
    """
    data = request.get_json(silent=True) or {}
    city_name = data.get('city') or data.get('name')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city name is required', 'status': 400}), 400

    city_name = city_name.strip()
    city = City.query.filter(City.name.ilike(city_name)).first()
    if not city:
        city = City(
            name=city_name,
            country=data.get('country'),
            lat=data.get('lat'),
            lon=data.get('lon'),
            is_favorite=True
        )
        db.session.add(city)
    else:
        city.is_favorite = True

    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': f"'{city.name}' added to favorites.",
        'city': city.to_dict()
    }), 200


@settings_bp.route('/favorites/<int:city_id>', methods=['DELETE'])
def remove_favorite(city_id):
    """Remove a city from favorites."""
    city = City.query.get(city_id)
    if not city:
        return jsonify({'error': f'City with ID {city_id} not found', 'status': 404}), 404

    city.is_favorite = False
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': f"'{city.name}' removed from favorites."
    }), 200


@settings_bp.route('/search-history', methods=['GET'])
def get_search_history():
    """Get recent search history entries."""
    limit = request.args.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    searches = (
        SearchHistory.query.order_by(SearchHistory.searched_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({
        'status': 'success',
        'count': len(searches),
        'history': [s.to_dict() for s in searches]
    }), 200


@settings_bp.route('/search-history', methods=['DELETE'])
def clear_search_history():
    """Clear all search history records."""
    SearchHistory.query.delete()
    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': 'Search history cleared successfully.'
    }), 200


@settings_bp.route('/config', methods=['GET'])
def get_config():
    """
    Get safe public application configuration (never exposes API keys or secrets).
    """
    return jsonify({
        'status': 'success',
        'api_configured': True,
        'weather_provider': 'Open-Meteo',
        'weather_api_key_required': False,
        'cache_timeout_seconds': Config.CACHE_TIMEOUT,
        'rate_limits': {
            'per_minute': Config.RATE_LIMIT_PER_MINUTE,
            'per_hour': Config.RATE_LIMIT_PER_HOUR
        },
        'supported_models': [
            {'id': 'temperature', 'name': 'Temperature Forecaster (Ridge Regression)'},
            {'id': 'anomalies', 'name': 'Weather Anomaly Detector (Isolation Forest)'}
        ],
        'default_city': 'Indore',
        'version': '1.0.0'
    }), 200
