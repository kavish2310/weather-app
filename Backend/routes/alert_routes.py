"""
Alert and Early Warning API endpoints.
"""

from flask import Blueprint, request, jsonify

from Backend.services.alert_service import AlertService

alert_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')
alert_service = AlertService()


@alert_bp.route('/', methods=['GET'])
@alert_bp.route('', methods=['GET'])
def get_alerts():
    """
    Get active alerts, optionally filtered by city.
    Query param:
      - city: City name (optional)
    """
    city = request.args.get('city')
    res = alert_service.get_active_alerts(city=city)
    return jsonify(res), 200


@alert_bp.route('/read/<int:alert_id>', methods=['POST'])
def mark_read(alert_id):
    """
    Mark an alert as read/acknowledged.
    """
    res = alert_service.mark_alert_read(alert_id)
    status_code = res.get('status', 200)
    return jsonify(res), status_code


@alert_bp.route('/history', methods=['GET'])
def get_history():
    """
    Get alert history for the past N days.
    Query params:
      - city: Filter by city (optional)
      - days: Number of days (default 7)
    """
    city = request.args.get('city')
    days = request.args.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7

    res = alert_service.get_alert_history(city=city, days=days)
    return jsonify(res), 200
