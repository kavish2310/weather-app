"""
Cyclone API endpoints for active tracking, tracks, affected regions, arrival estimates.
"""

from flask import Blueprint, request, jsonify

from Backend.services.cyclone_service import CycloneService
from Backend.models import Cyclone

cyclone_bp = Blueprint('cyclones', __name__, url_prefix='/api/cyclones')
cyclone_service = CycloneService()


@cyclone_bp.route('/active', methods=['GET'])
def get_active():
    """
    Get all currently active cyclones from authoritative sources (NOAA, JTWC, IMD).
    Returns real active cyclone data or clear 'No active cyclones reported' status.
    """
    result = cyclone_service.get_active_cyclones()
    return jsonify(result), result.get('status', 200)


@cyclone_bp.route('/track/<int:cyclone_id>', methods=['GET'])
def get_track(cyclone_id):
    """
    Get recorded and forecast track coordinates for a specific cyclone.
    """
    track = cyclone_service.get_cyclone_track(cyclone_id)
    if 'error' in track:
        return jsonify(track), track.get('status', 404)
    return jsonify({'status': 'success', 'data': track}), 200


@cyclone_bp.route('/affected-regions/<int:cyclone_id>', methods=['GET'])
def get_affected_regions(cyclone_id):
    """
    Get coastal regions and warning zones potentially affected by a cyclone.
    """
    regions = cyclone_service.get_affected_regions(cyclone_id)
    if 'error' in regions:
        return jsonify(regions), regions.get('status', 404)
    return jsonify({'status': 'success', 'data': regions}), 200


@cyclone_bp.route('/arrival', methods=['GET'])
def estimate_arrival():
    """
    Calculate estimated arrival window and distance for a given target coordinate.
    Query params:
      - cyclone_id: Cyclone ID
      - lat, lon: Target coordinates (e.g. coastal city)
    """
    cyclone_id = request.args.get('cyclone_id')
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    if not cyclone_id or lat is None or lon is None:
        return jsonify({
            'error': 'cyclone_id, lat, and lon query parameters are required',
            'status': 400
        }), 400

    try:
        c_id = int(cyclone_id)
        t_lat = float(lat)
        t_lon = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid parameter types. cyclone_id must be int, lat and lon float', 'status': 400}), 400

    estimate = cyclone_service.estimate_arrival(c_id, t_lat, t_lon)
    if 'error' in estimate:
        return jsonify(estimate), estimate.get('status', 400)
    return jsonify({'status': 'success', 'data': estimate}), 200


@cyclone_bp.route('/historical', methods=['GET'])
def get_historical():
    """
    Retrieve historical cyclones filtered by basin or year.
    Query params:
      - basin: e.g. NIO, Atlantic, Pacific
      - year: e.g. 2023
    """
    basin = request.args.get('basin')
    year = request.args.get('year')
    if year:
        try:
            year = int(year)
        except ValueError:
            year = None

    records = cyclone_service.get_historical_cyclones(basin=basin, year=year)
    return jsonify({'status': 'success', 'count': len(records), 'data': records}), 200
