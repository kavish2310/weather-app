"""
AlertService – manages weather alerts (auto-generated and manual).

Monitors weather thresholds for extreme heat, cold, wind, rainfall, and
visibility, creates database alerts, and retrieves alert history.
"""

import logging
from datetime import datetime, timedelta, timezone

from Backend.models import db, WeatherAlert, City

logger = logging.getLogger(__name__)


class AlertService:
    """Handles creation, retrieval, and management of weather alerts."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_active_alerts(self, city=None):
        """
        Retrieve active (non-expired) alerts, optionally filtered by city.

        Args:
            city (str | None): City name filter.

        Returns:
            dict: List of alert dicts.
        """
        now = datetime.now(timezone.utc)
        query = WeatherAlert.query.filter(
            (WeatherAlert.valid_until.is_(None)) | (WeatherAlert.valid_until >= now)
        )

        if city:
            city_obj = City.query.filter(City.name.ilike(city)).first()
            if city_obj:
                query = query.filter(
                    (WeatherAlert.city_id == city_obj.id) | (WeatherAlert.city_id.is_(None))
                )
            else:
                # No matching city; return only global (city_id IS NULL) alerts
                query = query.filter(WeatherAlert.city_id.is_(None))

        alerts = query.order_by(WeatherAlert.created_at.desc()).all()
        return {
            'alerts': [a.to_dict() for a in alerts],
            'count': len(alerts),
            'status': 200,
        }

    def create_alert(self, alert_data):
        """
        Create a new weather alert record.

        Args:
            alert_data (dict): Must include 'alert_type', 'severity', 'title'.

        Returns:
            dict: Created alert or error dict.
        """
        required = ('alert_type', 'severity', 'title')
        for field in required:
            if field not in alert_data:
                return {'error': f'Missing required field: {field}', 'status': 400}

        try:
            city_id = alert_data.get('city_id')
            if alert_data.get('city_name') and not city_id:
                city_obj = City.query.filter(
                    City.name.ilike(alert_data['city_name'])
                ).first()
                city_id = city_obj.id if city_obj else None

            alert = WeatherAlert(
                city_id=city_id,
                alert_type=alert_data['alert_type'],
                severity=alert_data['severity'],
                title=alert_data['title'],
                description=alert_data.get('description'),
                issuing_authority=alert_data.get('issuing_authority', 'System Auto-Alert'),
                issued_at=datetime.now(timezone.utc),
                valid_until=alert_data.get('valid_until'),
                affected_area=alert_data.get('affected_area'),
                recommended_action=alert_data.get('recommended_action'),
            )
            db.session.add(alert)
            db.session.commit()
            logger.info('Created alert: %s', alert.title)
            return {'alert': alert.to_dict(), 'status': 201}
        except Exception as exc:
            db.session.rollback()
            logger.error('Failed to create alert: %s', exc)
            return {'error': 'Failed to create alert', 'status': 500}

    def check_weather_thresholds(self, weather_data, city_name=None):
        """
        Evaluate weather data against danger thresholds and auto-generate alerts.

        Args:
            weather_data (dict): Current weather observation.
            city_name (str | None): City name for alert association.

        Returns:
            list[dict]: List of newly created alerts.
        """
        generated = []
        temperature = weather_data.get('temperature')
        wind_speed = weather_data.get('wind_speed')
        rainfall = weather_data.get('rainfall')
        visibility = weather_data.get('visibility')

        temp_alert = self._check_temperature_alert(temperature)
        if temp_alert:
            temp_alert['city_name'] = city_name
            result = self.create_alert(temp_alert)
            if 'alert' in result:
                generated.append(result['alert'])

        wind_alert = self._check_wind_alert(wind_speed)
        if wind_alert:
            wind_alert['city_name'] = city_name
            result = self.create_alert(wind_alert)
            if 'alert' in result:
                generated.append(result['alert'])

        rain_alert = self._check_rainfall_alert(rainfall)
        if rain_alert:
            rain_alert['city_name'] = city_name
            result = self.create_alert(rain_alert)
            if 'alert' in result:
                generated.append(result['alert'])

        vis_alert = self._check_visibility_alert(visibility)
        if vis_alert:
            vis_alert['city_name'] = city_name
            result = self.create_alert(vis_alert)
            if 'alert' in result:
                generated.append(result['alert'])

        return generated

    def mark_alert_read(self, alert_id):
        """
        Mark an alert as read.

        Args:
            alert_id (int): Alert primary key.

        Returns:
            dict: Updated alert or error dict.
        """
        alert = WeatherAlert.query.get(alert_id)
        if not alert:
            return {'error': f'Alert {alert_id} not found', 'status': 404}
        try:
            alert.is_read = True
            db.session.commit()
            return {'alert': alert.to_dict(), 'status': 200}
        except Exception as exc:
            db.session.rollback()
            logger.error('Failed to mark alert %s read: %s', alert_id, exc)
            return {'error': 'Failed to update alert', 'status': 500}

    def get_alert_history(self, city=None, days=7):
        """
        Retrieve alert history for the past N days.

        Args:
            city (str | None): City name filter.
            days (int): Look-back window.

        Returns:
            dict: List of alert dicts.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = WeatherAlert.query.filter(WeatherAlert.created_at >= since)

        if city:
            city_obj = City.query.filter(City.name.ilike(city)).first()
            if city_obj:
                query = query.filter(
                    (WeatherAlert.city_id == city_obj.id) | (WeatherAlert.city_id.is_(None))
                )

        alerts = query.order_by(WeatherAlert.created_at.desc()).all()
        return {
            'alerts': [a.to_dict() for a in alerts],
            'count': len(alerts),
            'days': days,
            'status': 200,
        }

    # ------------------------------------------------------------------
    # Threshold checkers
    # ------------------------------------------------------------------

    def _check_temperature_alert(self, temp):
        """
        Check for extreme temperature conditions.

        Triggers alert for extreme heat (>45 °C) or extreme cold (<0 °C).

        Args:
            temp (float | None): Temperature in Celsius.

        Returns:
            dict | None: Alert data dict or None.
        """
        if temp is None:
            return None

        if temp > 45:
            return {
                'alert_type': 'extreme_heat',
                'severity': 'extreme',
                'title': f'Extreme Heat Warning – {temp}°C',
                'description': (
                    f'Temperature has reached {temp}°C, posing severe health risks '
                    'including heat stroke and dehydration.'
                ),
                'recommended_action': (
                    'Stay indoors in air-conditioned spaces. Drink plenty of water. '
                    'Avoid outdoor activities. Check on elderly and vulnerable individuals.'
                ),
                'valid_until': datetime.now(timezone.utc) + timedelta(hours=6),
            }
        if temp < 0:
            return {
                'alert_type': 'extreme_cold',
                'severity': 'high',
                'title': f'Extreme Cold Warning – {temp}°C',
                'description': (
                    f'Temperature has dropped to {temp}°C. Risk of hypothermia and '
                    'frostbite for exposed individuals.'
                ),
                'recommended_action': (
                    'Wear multiple layers of warm clothing. Limit time outdoors. '
                    'Ensure heating systems are functioning. Protect exposed pipes.'
                ),
                'valid_until': datetime.now(timezone.utc) + timedelta(hours=12),
            }
        return None

    def _check_wind_alert(self, wind_speed):
        """
        Check for dangerous wind speeds.

        Triggers alert when wind exceeds 60 km/h (OWM reports m/s, converted here).

        Args:
            wind_speed (float | None): Wind speed in m/s from OWM.

        Returns:
            dict | None: Alert data dict or None.
        """
        if wind_speed is None:
            return None
        wind_kmh = wind_speed * 3.6  # m/s → km/h
        if wind_kmh >= 120:
            severity = 'extreme'
            label = 'Hurricane-Force'
        elif wind_kmh >= 90:
            severity = 'high'
            label = 'Storm-Force'
        elif wind_kmh >= 60:
            severity = 'moderate'
            label = 'High'
        else:
            return None

        return {
            'alert_type': 'high_wind',
            'severity': severity,
            'title': f'{label} Wind Warning – {round(wind_kmh, 1)} km/h',
            'description': (
                f'Wind speeds of {round(wind_kmh, 1)} km/h detected. '
                'Risk of structural damage and flying debris.'
            ),
            'recommended_action': (
                'Secure loose outdoor objects. Avoid driving. Stay away from windows. '
                'Seek shelter in a sturdy building.'
            ),
            'valid_until': datetime.now(timezone.utc) + timedelta(hours=6),
        }

    def _check_rainfall_alert(self, rainfall):
        """
        Check for heavy rainfall conditions.

        Triggers alert when rainfall exceeds 50 mm in the last measurement period.

        Args:
            rainfall (float | None): Rainfall in mm.

        Returns:
            dict | None: Alert data dict or None.
        """
        if rainfall is None:
            return None
        if rainfall < 50:
            return None

        if rainfall >= 115:
            severity = 'extreme'
            label = 'Extremely Heavy'
        elif rainfall >= 65:
            severity = 'high'
            label = 'Very Heavy'
        else:
            severity = 'moderate'
            label = 'Heavy'

        return {
            'alert_type': 'heavy_rainfall',
            'severity': severity,
            'title': f'{label} Rainfall Alert – {rainfall} mm',
            'description': (
                f'{rainfall} mm of rainfall recorded. Urban flooding and waterlogging expected.'
            ),
            'recommended_action': (
                'Avoid low-lying areas. Do not cross flooded roads. '
                'Keep emergency supplies ready. Follow local authority guidance.'
            ),
            'valid_until': datetime.now(timezone.utc) + timedelta(hours=12),
        }

    def _check_visibility_alert(self, visibility):
        """
        Check for poor visibility conditions.

        Triggers alert when visibility drops below 1000 m.

        Args:
            visibility (int | None): Visibility in metres.

        Returns:
            dict | None: Alert data dict or None.
        """
        if visibility is None:
            return None
        if visibility >= 1000:
            return None

        if visibility < 200:
            severity = 'extreme'
            label = 'Dense Fog'
        elif visibility < 500:
            severity = 'high'
            label = 'Thick Fog'
        else:
            severity = 'moderate'
            label = 'Reduced Visibility'

        return {
            'alert_type': 'poor_visibility',
            'severity': severity,
            'title': f'{label} Alert – Visibility {visibility} m',
            'description': (
                f'Visibility reduced to {visibility} metres due to fog, smog, or haze.'
            ),
            'recommended_action': (
                'Avoid driving if possible. Use fog lights and reduce speed. '
                'Maintain extra distance from vehicles ahead. '
                'Be alert for pedestrians and cyclists.'
            ),
            'valid_until': datetime.now(timezone.utc) + timedelta(hours=6),
        }
