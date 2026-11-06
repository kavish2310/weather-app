"""
API Routes package for Weather Intelligence & Cyclone Monitoring System.
"""

from Backend.routes.weather_routes import weather_bp
from Backend.routes.cyclone_routes import cyclone_bp
from Backend.routes.analytics_routes import analytics_bp
from Backend.routes.risk_routes import risk_bp
from Backend.routes.alert_routes import alert_bp
from Backend.routes.settings_routes import settings_bp

__all__ = [
    'weather_bp',
    'cyclone_bp',
    'analytics_bp',
    'risk_bp',
    'alert_bp',
    'settings_bp'
]
