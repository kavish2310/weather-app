"""
Disaster Risk Assessment API endpoints.
"""

from flask import Blueprint, request, jsonify

from Backend.services.risk_service import RiskAssessmentService
from Backend.services.weather_service import WeatherService
from Backend.services.cyclone_service import CycloneService
from Backend.models import Cyclone
from Backend.utils import haversine_distance

risk_bp = Blueprint('risk', __name__, url_prefix='/api/risk')
risk_service = RiskAssessmentService()
weather_service = WeatherService()
cyclone_service = CycloneService()


@risk_bp.route('/assessment', methods=['GET'])
def get_risk_assessment():
    """
    Perform a comprehensive multi-hazard disaster risk assessment for a city.
    Query param:
      - city: City name (e.g. "Mumbai")
    """
    city_name = request.args.get('city')
    if not city_name or not city_name.strip():
        return jsonify({'error': 'city parameter is required', 'status': 400}), 400

    weather_data = weather_service.get_current_weather(city_name.strip())
    if 'error' in weather_data:
        # If API key is missing or weather fails, provide default base assessment or return error
        return jsonify({
            'error': f"Failed to retrieve weather data for '{city_name}': {weather_data['error']}",
            'status': weather_data.get('status', 400)
        }), weather_data.get('status', 400)

    # Check for active cyclones near or relevant to this city
    active_res = cyclone_service.get_active_cyclones()
    cyclones = active_res.get('cyclones', [])
    city_lat = weather_data.get('lat')
    city_lon = weather_data.get('lon')
    geolocated_cyclones = [
        cyclone for cyclone in cyclones
        if cyclone.get('lat') is not None and cyclone.get('lon') is not None
    ]
    relevant_cyclone = None
    if city_lat is not None and city_lon is not None and geolocated_cyclones:
        relevant_cyclone = min(
            geolocated_cyclones,
            key=lambda cyclone: haversine_distance(
                cyclone['lat'], cyclone['lon'], city_lat, city_lon
            )
        )
    elif cyclones:
        relevant_cyclone = cyclones[0]
    elif active_res.get('status') == 200:
        relevant_cyclone = {'feed_checked': True, 'no_active_cyclones': True}

    assessment = risk_service.assess_risk(
        city=city_name.strip(),
        weather_data=weather_data,
        cyclone_data=relevant_cyclone
    )
    assessment['cyclone_feed_checked_at'] = active_res.get('checked_at')

    return jsonify({'status': 'success', 'data': assessment}), 200


@risk_bp.route('/cyclone-risk', methods=['GET'])
def get_cyclone_specific_risk():
    """
    Evaluate cyclone proximity risk for a specific cyclone and city.
    Query params:
      - cyclone_id: Cyclone ID
      - city: Coastal city name
    """
    cyclone_id = request.args.get('cyclone_id')
    city_name = request.args.get('city')

    if not cyclone_id or not city_name:
        return jsonify({'error': 'Both cyclone_id and city query parameters are required', 'status': 400}), 400

    try:
        c_id = int(cyclone_id)
    except ValueError:
        return jsonify({'error': 'cyclone_id must be an integer', 'status': 400}), 400

    cyclone = Cyclone.query.get(c_id)
    if not cyclone:
        return jsonify({'error': f'Cyclone {cyclone_id} not found', 'status': 404}), 404

    weather_data = weather_service.get_current_weather(city_name.strip())
    assessment = risk_service.assess_risk(
        city=city_name.strip(),
        weather_data=weather_data if 'error' not in weather_data else {},
        cyclone_data=cyclone.to_dict()
    )

    return jsonify({'status': 'success', 'data': assessment}), 200
