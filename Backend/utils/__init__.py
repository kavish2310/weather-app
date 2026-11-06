"""
Utility functions for the Weather Intelligence & Cyclone Monitoring System.

Includes helpers for temperature formatting, wind direction conversion,
heat-index / wind-chill calculations, geo-distance (Haversine), caching,
datetime formatting, input validation, and safe HTTP requests.
"""

import math
import re
import time
import logging
from datetime import datetime, timezone
from functools import wraps

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory response cache
# ---------------------------------------------------------------------------
_cache: dict = {}


class ValidationResult(tuple):
    """A tuple that evaluates its truthiness based on its first element (is_valid)."""
    def __new__(cls, is_valid, msg):
        return super().__new__(cls, (is_valid, msg))

    def __bool__(self):
        return bool(self[0])


def format_temperature(temp, unit='celsius'):
    """
    Format a temperature value with the appropriate unit symbol.

    Args:
        temp: Temperature value (numeric).
        unit: 'celsius', 'fahrenheit', or 'kelvin'.

    Returns:
        str: Formatted temperature string, e.g. "23.5°C".
    """
    if temp is None:
        return 'N/A'
    u = unit.lower()
    if u == 'fahrenheit':
        temp = (temp * 9 / 5) + 32
    elif u == 'kelvin':
        temp = temp + 273.15

    symbols = {'celsius': '°C', 'fahrenheit': '°F', 'kelvin': 'K'}
    symbol = symbols.get(u, '°C')
    return f'{round(temp, 1)}{symbol}'


def format_wind_direction(degrees):
    """
    Convert wind-direction degrees to a compass label.

    Args:
        degrees: Wind direction in meteorological degrees (0–360).

    Returns:
        str: Compass direction (N, NE, E, SE, S, SW, W, NW).
    """
    if degrees is None:
        return 'N/A'
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    idx = round(degrees / 45) % 8
    return directions[idx]


def calculate_heat_index(temp, humidity):
    """
    Calculate the heat index (apparent temperature in hot conditions).

    Uses the Rothfusz regression equation (temp in °C, humidity in %).

    Args:
        temp: Air temperature in Celsius.
        humidity: Relative humidity percentage.

    Returns:
        float | None: Heat index in Celsius, or None if inputs are invalid.
    """
    if temp is None or humidity is None:
        return None
    # Convert to Fahrenheit for the standard formula
    t_f = temp * 9 / 5 + 32
    if t_f < 80:
        # Simple formula for lower temperatures
        hi_f = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + humidity * 0.094)
        return round((hi_f - 32) * 5 / 9, 1)
    rh = humidity
    hi_f = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * t_f ** 2
        - 0.05481717 * rh ** 2
        + 0.00122874 * t_f ** 2 * rh
        + 0.00085282 * t_f * rh ** 2
        - 0.00000199 * t_f ** 2 * rh ** 2
    )
    # Adjustments
    if rh < 13 and 80 <= t_f <= 112:
        hi_f -= ((13 - rh) / 4) * math.sqrt((17 - abs(t_f - 95)) / 17)
    elif rh > 85 and 80 <= t_f <= 87:
        hi_f += ((rh - 85) / 10) * ((87 - t_f) / 5)
    return round((hi_f - 32) * 5 / 9, 1)


def calculate_wind_chill(temp, wind_speed):
    """
    Calculate the wind chill temperature.

    Uses the North American Wind Chill Index formula (temp in °C,
    wind_speed in km/h).

    Args:
        temp: Air temperature in Celsius.
        wind_speed: Wind speed in km/h.

    Returns:
        float | None: Wind chill in Celsius, or None if conditions don't apply.
    """
    if temp is None or wind_speed is None:
        return None
    if temp > 10 or wind_speed < 4.8:
        return temp  # Wind chill not applicable
    wc = (
        13.12
        + 0.6215 * temp
        - 11.37 * (wind_speed ** 0.16)
        + 0.3965 * temp * (wind_speed ** 0.16)
    )
    return round(wc, 1)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: Latitude/longitude of point 1 in decimal degrees.
        lat2, lon2: Latitude/longitude of point 2 in decimal degrees.

    Returns:
        float: Distance in kilometres.
    """
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def format_datetime(dt_object):
    """
    Format a datetime object to an ISO-8601 string.

    Args:
        dt_object: A datetime instance or Unix timestamp (int/float).

    Returns:
        str | None: ISO-formatted string, or None if input is None.
    """
    if dt_object is None:
        return None
    if isinstance(dt_object, (int, float)):
        dt_object = datetime.fromtimestamp(dt_object, tz=timezone.utc)
    if isinstance(dt_object, datetime):
        return dt_object.isoformat()
    return str(dt_object)


def validate_city_name(name):
    """
    Validate a city name string.

    Args:
        name: The city name to validate.

    Returns:
        ValidationResult: (is_valid: bool, sanitised_name_or_error: str).
    """
    if not name or not isinstance(name, str):
        return ValidationResult(False, 'City name is required.')
    sanitised = name.strip()
    if len(sanitised) < 2:
        return ValidationResult(False, 'City name must be at least 2 characters.')
    if len(sanitised) > 128:
        return ValidationResult(False, 'City name must be fewer than 128 characters.')
    if not re.match(r"^[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF\s\-'.]+$", sanitised):
        return ValidationResult(False, 'City name contains invalid characters.')
    return ValidationResult(True, sanitised)


def cache_response(timeout=300):
    """
    Decorator that caches a function's return value for *timeout* seconds.

    Uses a simple in-memory dict keyed on function name + args.

    Args:
        timeout: Cache lifetime in seconds (default 300).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build a hashable cache key from positional + keyword args
            key_parts = [func.__name__] + [str(a) for a in args]
            key_parts += [f'{k}={v}' for k, v in sorted(kwargs.items())]
            cache_key = '|'.join(key_parts)

            now = time.time()
            if cache_key in _cache:
                cached_value, cached_at = _cache[cache_key]
                if now - cached_at < timeout:
                    logger.debug('Cache hit for %s', cache_key)
                    return cached_value

            result = func(*args, **kwargs)
            _cache[cache_key] = (result, now)
            return result
        return wrapper
    return decorator


def safe_api_request(url, params=None, timeout=10, headers=None):
    """
    Perform a GET request with error handling.

    Args:
        url: Target URL.
        params: Optional query-string parameters dict.
        timeout: Request timeout in seconds.
        headers: Optional HTTP headers dict.

    Returns:
        dict: On success, the JSON-decoded response with an added 'status' key
              of 200. On failure, an 'error' key with human-readable message
              and the HTTP or exception-derived 'status' code.
    """
    try:
        response = requests.get(url, params=params, timeout=timeout, headers=headers)
        response.raise_for_status()
        data = response.json()
        data['status'] = 200
        return data
    except requests.exceptions.Timeout:
        logger.error('Request to %s timed out after %ss', url, timeout)
        return {'error': f'Request timed out after {timeout}s', 'status': 408}
    except requests.exceptions.ConnectionError:
        logger.error('Connection error when reaching %s', url)
        return {'error': 'Unable to connect to the API server', 'status': 503}
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 500
        logger.error('HTTP %s from %s', status_code, url)
        return {'error': f'API returned HTTP {status_code}', 'status': status_code}
    except requests.exceptions.RequestException as exc:
        logger.error('Request error for %s: %s', url, exc)
        return {'error': str(exc), 'status': 500}
    except ValueError:
        logger.error('Non-JSON response from %s', url)
        return {'error': 'Invalid JSON response from API', 'status': 502}
