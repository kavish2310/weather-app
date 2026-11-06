"""
Main Flask Application Factory for Weather Intelligence & Cyclone Monitoring System.
"""

import os
import sys
import logging
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Ensure project root and Backend directory are on Python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from Backend.config import Config
from Backend.database import init_db
from Backend.routes import (
    weather_bp,
    cyclone_bp,
    analytics_bp,
    risk_bp,
    alert_bp,
    settings_bp
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('weather_app')


def create_app(config_class=Config):
    """
    Application factory pattern.
    Configures database, CORS, routes, static file serving, and error handling.
    """
    frontend_dir = os.path.join(PROJECT_ROOT, 'Frontend')
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.config.from_object(config_class)

    if os.environ.get('VERCEL') and app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:'):
        raise RuntimeError(
            'Vercel requires a persistent PostgreSQL DATABASE_URL. '
            'Configure one in the Vercel project environment variables.'
        )

    # Enable CORS for local API access
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database
    init_db(app)

    # Register API Blueprints
    app.register_blueprint(weather_bp)
    app.register_blueprint(cyclone_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(settings_bp)

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': 'Weather Intelligence & Cyclone Monitoring System',
            'version': '1.0.0',
            'providers': {
                'weather': {
                    'name': 'Open-Meteo',
                    'api_key_required': False
                },
                'air_quality': {
                    'name': 'Open-Meteo Air Quality',
                    'api_key_required': False
                },
                'cyclones': ['NOAA NHC', 'JTWC', 'IMD']
            }
        }), 200

    # Static file routes for Frontend
    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'weather-intelligence.html')

    @app.route('/pages/<path:filename>')
    def serve_pages(filename):
        pages_dir = os.path.join(frontend_dir, 'pages')
        return send_from_directory(pages_dir, filename)

    @app.route('/css/<path:filename>')
    def serve_css(filename):
        css_dir = os.path.join(frontend_dir, 'css')
        return send_from_directory(css_dir, filename)

    @app.route('/js/<path:filename>')
    def serve_js(filename):
        js_dir = os.path.join(frontend_dir, 'js')
        return send_from_directory(js_dir, filename)

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        assets_dir = os.path.join(frontend_dir, 'assets')
        return send_from_directory(assets_dir, filename)

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'error': 'Resource not found',
            'status': 404,
            'message': str(error)
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal server error',
            'status': 500,
            'message': 'An unexpected error occurred on the server.'
        }), 500

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            'error': 'Bad request',
            'status': 400,
            'message': str(error)
        }), 400

    return app


if __name__ == '__main__':
    application = create_app()
    logger.info("Starting Weather Intelligence System on http://127.0.0.1:5000")
    application.run(host='127.0.0.1', port=5000, debug=Config.DEBUG)
