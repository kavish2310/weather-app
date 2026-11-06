"""
Configuration module for the Weather Intelligence & Cyclone Monitoring System.

Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))


class Config:
    """Application configuration loaded from environment variables."""

    # Flask core settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

    # Database settings
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, 'data')

    _db_env = os.environ.get('DATABASE_URL', '')
    if _db_env.startswith('sqlite:///') and ':memory:' not in _db_env:
        _rel_path = _db_env.replace('sqlite:///', '')
        if not os.path.isabs(_rel_path) and not (len(_rel_path) > 1 and _rel_path[1] == ':'):
            _abs_path = os.path.join(BASE_DIR, _rel_path).replace('\\', '/')
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{_abs_path}'
        else:
            _clean_path = _rel_path.replace('\\', '/')
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{_clean_path}'
    elif _db_env:
        if _db_env.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = _db_env.replace(
                'postgres://', 'postgresql+psycopg://', 1
            )
        elif _db_env.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = _db_env.replace(
                'postgresql://', 'postgresql+psycopg://', 1
            )
        else:
            SQLALCHEMY_DATABASE_URI = _db_env
    else:
        _default_db = os.path.join(DATA_DIR, 'weather.db').replace('\\', '/')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_default_db}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Legacy OpenWeatherMap settings retained for configuration compatibility.
    OPENWEATHERMAP_API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY', '')
    OPENWEATHERMAP_BASE_URL = os.environ.get(
        'OPENWEATHERMAP_BASE_URL',
        'https://api.openweathermap.org/data/2.5'
    )
    OPENWEATHERMAP_GEO_URL = 'https://api.openweathermap.org/geo/1.0'

    # Cache settings
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))  # 5 minutes default

    # Rate limiting settings
    RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', 60))
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', 1000))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        warnings = []
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            warnings.append(
                'Using default SECRET_KEY. Set FLASK_SECRET_KEY for production.'
            )
        return warnings
