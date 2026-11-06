"""
Tests for Weather Intelligence & Cyclone Monitoring System
"""
import os
import sys
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

# Add project root and Backend to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'Backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from Backend.app import create_app
from Backend.models import db, City, WeatherObservation, WeatherForecast, Cyclone, WeatherAlert, SearchHistory


class TestConfig:
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'


class TestHealthEndpoint(unittest.TestCase):
    """Test the health check endpoint."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_check(self):
        """Test /api/health returns 200."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_health_check_has_timestamp(self):
        """Test health check includes timestamp."""
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        self.assertIn('timestamp', data)

    def test_localhost_root_serves_weather_intelligence_dashboard(self):
        """The shareable localhost URL should open the dashboard, not a file listing."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.content_type)
        self.assertIn(b'Weather Intelligence', response.data)
        self.assertIn(b'wiTemperatureChart', response.data)
        response.close()

    def test_vercel_without_postgres_uses_writable_temporary_database(self):
        """Vercel must start without a configured Postgres URL."""
        class VercelConfig(TestConfig):
            SQLALCHEMY_DATABASE_URI = 'sqlite:///data/weather.db'

        with patch.dict(os.environ, {'VERCEL': '1'}):
            with patch('Backend.app.init_db'):
                app = create_app(VercelConfig)

        expected_path = os.path.join(
            tempfile.gettempdir(), 'weather-intelligence.db'
        ).replace('\\', '/')
        self.assertEqual(
            app.config['SQLALCHEMY_DATABASE_URI'],
            f'sqlite:///{expected_path}'
        )


class TestWeatherEndpoints(unittest.TestCase):
    """Test weather API endpoints."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_current_weather_no_city(self):
        """Test current weather without city parameter returns error."""
        response = self.client.get('/api/weather/current')
        self.assertIn(response.status_code, [400, 422])

    def test_current_weather_empty_city(self):
        """Test current weather with empty city returns error."""
        response = self.client.get('/api/weather/current?city=')
        self.assertIn(response.status_code, [400, 422])

    def test_forecast_no_city(self):
        """Test forecast without city parameter returns error."""
        response = self.client.get('/api/weather/forecast')
        self.assertIn(response.status_code, [400, 422])

    def test_multiple_no_cities(self):
        """Test multiple cities without parameter returns error."""
        response = self.client.get('/api/weather/multiple')
        self.assertIn(response.status_code, [400, 422])

    def test_search_no_query(self):
        """Test search without query returns error."""
        response = self.client.get('/api/weather/search')
        self.assertIn(response.status_code, [400, 422])


class TestAnalyticsTimeseriesEndpoint(unittest.TestCase):
    """Test the combined historical and forecast chart feed."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            city = City(name='Indore', country='IN')
            db.session.add(city)
            db.session.flush()
            now = datetime.now()
            db.session.add(WeatherObservation(
                city_id=city.id,
                temperature=25.0,
                feels_like=24.0,
                humidity=60,
                pressure=1012,
                wind_speed=4.0,
                wind_deg=90,
                source='Open-Meteo (live model data)',
                observed_at=now
            ))
            db.session.add(WeatherObservation(
                city_id=city.id,
                temperature=26.0,
                source='Open-Meteo (live model data)',
                observed_at=now
            ))
            db.session.add(WeatherForecast(
                city_id=city.id,
                forecast_dt=now + timedelta(hours=3),
                temperature=27.0,
                feels_like=26.0,
                humidity=55,
                pressure=1011,
                wind_speed=5.0,
                wind_deg=110,
                source='Open-Meteo'
            ))
            db.session.add(WeatherObservation(
                city_id=city.id,
                temperature=99.0,
                observed_at=now
            ))
            db.session.add(WeatherForecast(
                city_id=city.id,
                forecast_dt=now + timedelta(hours=4),
                temperature=99.0
            ))
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_timeseries_returns_observations_and_forecasts_for_all_chart_metrics(self):
        response = self.client.get('/api/analytics/timeseries?city=Indore&period=24h')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['city'], 'Indore')
        self.assertEqual(len(data['observations']), 1)
        self.assertEqual(len(data['forecasts']), 1)
        self.assertEqual(data['observations'][0]['source'], 'Open-Meteo (live model data)')
        self.assertEqual(data['forecasts'][0]['source'], 'Open-Meteo')
        self.assertEqual(data['observations'][0]['temperature'], 26.0)
        for field in ('temperature', 'feels_like', 'humidity', 'pressure', 'wind_speed', 'wind_deg'):
            self.assertIn(field, data['observations'][0])
            self.assertIn(field, data['forecasts'][0])

    def test_timeseries_requires_city(self):
        response = self.client.get('/api/analytics/timeseries')
        self.assertEqual(response.status_code, 400)


class TestLiveWeatherProvider(unittest.TestCase):
    """Verify live weather parsing and explicit provider failures."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_current_weather_uses_live_open_meteo_values_and_saves_forecast(self):
        from Backend.services.weather_service import WeatherService

        times = [f'2026-11-06T{hour:02d}:00' for hour in range(24)]
        hourly = {
            'time': times,
            'temperature_2m': [21.5] * 24,
            'relative_humidity_2m': [72] * 24,
            'apparent_temperature': [20.0] * 24,
            'precipitation_probability': [10] * 24,
            'precipitation': [0.0] * 24,
            'weather_code': [2] * 24,
            'cloud_cover': [35] * 24,
            'pressure_msl': [1012.0] * 24,
            'surface_pressure': [950.0] * 24,
            'wind_speed_10m': [4.5] * 24,
            'wind_direction_10m': [180] * 24,
            'wind_gusts_10m': [7.0] * 24,
            'uv_index': [3.0] * 24,
            'visibility': [12000] * 24,
            'is_day': [1] * 24,
        }
        open_meteo = {
            'current': {
                'time': '2026-11-06T10:00',
                'temperature_2m': 22.4,
                'relative_humidity_2m': 68,
                'apparent_temperature': 21.1,
                'is_day': 1,
                'precipitation': 0.1,
                'weather_code': 1,
                'cloud_cover': 20,
                'pressure_msl': 1011.5,
                'surface_pressure': 949.0,
                'wind_speed_10m': 3.2,
                'wind_direction_10m': 120,
                'wind_gusts_10m': 5.4,
                'uv_index': 4.2,
                'visibility': 15000,
            },
            'daily': {
                'sunrise': ['2026-11-06T06:21'],
                'sunset': ['2026-11-06T17:42'],
                'temperature_2m_min': [18.0],
                'temperature_2m_max': [29.0],
            },
            'hourly': hourly,
        }

        def fake_request(url, params=None, **kwargs):
            if 'geocoding-api' in url:
                return {'results': [{
                    'name': 'Indore',
                    'country_code': 'IN',
                    'latitude': 22.72,
                    'longitude': 75.85,
                    'timezone': 'Asia/Kolkata',
                }]}
            if 'air-quality-api' in url:
                return {'current': {'us_aqi': 42, 'pm2_5': 8.1}}
            return open_meteo

        with patch('Backend.services.weather_service.safe_api_request', side_effect=fake_request):
            result = WeatherService().get_current_weather('Indore')

        self.assertEqual(result['source'], 'Open-Meteo (live model data)')
        self.assertEqual(result['temperature'], 22.4)
        self.assertEqual(result['humidity'], 68)
        self.assertEqual(result['pressure'], 1011.5)
        self.assertEqual(result['air_quality_index'], 42)
        city = City.query.filter_by(name='Indore').first()
        self.assertEqual(city.observations.count(), 1)
        self.assertEqual(city.forecasts.count(), 8)

    def test_live_provider_error_does_not_return_synthetic_weather(self):
        from Backend.services.weather_service import WeatherService

        with patch(
            'Backend.services.weather_service.safe_api_request',
            return_value={'error': 'Unable to connect to the API server', 'status': 503}
        ):
            result = WeatherService().get_current_weather('Indore')

        self.assertEqual(result['status'], 503)
        self.assertIn('error', result)
        self.assertNotIn('temperature', result)

    def test_historical_archive_returns_distinct_dates_and_persists_verified_samples(self):
        from Backend.services.weather_service import WeatherService

        city = City(name='Archive Test City', country='IN', lat=23.18, lon=75.78)
        db.session.add(city)
        db.session.commit()
        end_date = (datetime.now().date() - timedelta(days=1))
        start_date = end_date - timedelta(days=1)
        times = [
            f'{day.isoformat()}T{hour:02d}:00'
            for day in (start_date, end_date)
            for hour in range(24)
        ]
        archive_payload = {
            'timezone': 'Asia/Kolkata',
            'hourly': {
                'time': times,
                'temperature_2m': [20 + index / 24 for index in range(48)],
                'relative_humidity_2m': [50 + index % 20 for index in range(48)],
                'pressure_msl': [1010 + index / 10 for index in range(48)],
                'wind_speed_10m': [2 + index / 10 for index in range(48)],
                'wind_direction_10m': [index * 10 % 360 for index in range(48)],
                'weather_code': [0] * 48,
            },
        }

        with patch(
            'Backend.services.weather_service.safe_api_request',
            return_value=archive_payload
        ) as request:
            result = WeatherService().get_historical_archive('Archive Test City', days=2)

        self.assertEqual(len(result['records']), 2)
        self.assertNotEqual(
            result['records'][0]['observed_at'][:10],
            result['records'][1]['observed_at'][:10]
        )
        self.assertNotEqual(
            result['records'][0]['temperature'],
            result['records'][1]['temperature']
        )
        self.assertTrue(all(
            record['source'] == 'Open-Meteo archive (reanalysis)'
            for record in result['records']
        ))
        self.assertEqual(
            WeatherObservation.query.filter_by(
                city_id=city.id,
                source='Open-Meteo archive (reanalysis)'
            ).count(),
            16
        )
        self.assertEqual(request.call_count, 1)


class TestCycloneEndpoints(unittest.TestCase):
    """Test cyclone API endpoints."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_active_cyclones_endpoint(self):
        """Test active cyclones endpoint returns 200."""
        with patch(
            'Backend.routes.cyclone_routes.cyclone_service.get_active_cyclones',
            return_value={'cyclones': [], 'count': 0, 'sources_checked': ['JTWC'], 'status': 200}
        ):
            response = self.client.get('/api/cyclones/active')
        self.assertEqual(response.status_code, 200)

    def test_active_cyclone_feed_includes_check_time_and_source_status(self):
        from Backend.services.cyclone_service import CycloneService

        service = CycloneService()
        with patch.object(service, '_fetch_nhc_feed', return_value=[]), \
             patch.object(service, '_fetch_jtwc_feed', return_value=[]), \
             patch.object(service, '_fetch_imd_feed', return_value=[]), \
             patch.object(service, '_save_cyclone'):
            response = service.get_active_cyclones()

        self.assertEqual(response['status'], 200)
        self.assertEqual(response['sources_checked'], [
            'NOAA NHC Atlantic', 'NOAA NHC Eastern Pacific', 'JTWC', 'IMD India'
        ])
        self.assertIsNotNone(response['checked_at'])

    def test_jtwc_warning_parser_reads_official_position_and_winds(self):
        from Backend.services.cyclone_service import CycloneService

        warning = """SUBJ/TROPICAL DEPRESSION 31W (THIRTYONE) WARNING NR 001//
WARNING POSITION:
060600Z --- NEAR 18.0N 149.0E
MOVEMENT PAST SIX HOURS - 310 DEGREES AT 18 KTS
PRESENT WIND DISTRIBUTION:
MAX SUSTAINED WINDS - 025 KT, GUSTS 035 KT
MINIMUM CENTRAL PRESSURE - 1000 MB
"""
        result = CycloneService()._parse_jtwc_warning(
            warning,
            'https://www.metoc.navy.mil/jtwc/products/wp3126web.txt'
        )
        self.assertEqual(result['name'], 'TROPICAL DEPRESSION 31W (THIRTYONE)')
        self.assertEqual(result['lat'], 18.0)
        self.assertEqual(result['lon'], 149.0)
        self.assertEqual(result['max_wind_speed'], 46.3)
        self.assertEqual(result['movement_speed'], 33.3)
        self.assertEqual(result['identifier'], 'JTWC-WP3126')

    def test_cyclone_track_not_found(self):
        """Test cyclone track for non-existent cyclone."""
        response = self.client.get('/api/cyclones/track/999')
        self.assertIn(response.status_code, [404, 200])


class TestAlertEndpoints(unittest.TestCase):
    """Test alert API endpoints."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_alerts(self):
        """Test getting all alerts."""
        response = self.client.get('/api/alerts/')
        self.assertEqual(response.status_code, 200)

    def test_get_alerts_with_city(self):
        """Test getting alerts for a specific city."""
        response = self.client.get('/api/alerts/?city=Mumbai')
        self.assertEqual(response.status_code, 200)


class TestRiskEndpoints(unittest.TestCase):
    """Test risk assessment endpoints."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_risk_assessment_no_city(self):
        """Test risk assessment without city returns error."""
        response = self.client.get('/api/risk/assessment')
        self.assertIn(response.status_code, [400, 422])

    def test_assessment_returns_live_open_meteo_values_and_checked_empty_cyclone_feed(self):
        weather = {
            'city': 'Mumbai',
            'lat': 19.076,
            'lon': 72.8777,
            'temperature': 29.8,
            'wind_speed': 2.4,
            'wind_speed_unit': 'km/h',
            'rainfall': 0,
            'pressure': 1014.1,
            'humidity': 68,
            'visibility': 10000,
            'source': 'Open-Meteo (live model data)',
            'country': 'IN',
            'observed_at': '2026-11-06T12:00:00Z',
        }
        with patch('Backend.routes.risk_routes.weather_service.get_current_weather', return_value=weather), \
             patch('Backend.routes.risk_routes.cyclone_service.get_active_cyclones', return_value={
                 'cyclones': [], 'status': 200, 'checked_at': '2026-11-06T12:05:00Z'
             }):
            response = self.client.get('/api/risk/assessment?city=Mumbai')

        self.assertEqual(response.status_code, 200)
        assessment = response.get_json()['data']
        self.assertEqual(assessment['overall_score'], 0)
        self.assertEqual(assessment['weather_summary']['wind_speed_kmh'], 2.4)
        self.assertEqual(assessment['weather_summary']['rainfall_mm'], 0)
        self.assertEqual(assessment['individual_risks']['wind'], 0)
        self.assertEqual(assessment['individual_risks']['rainfall'], 0)
        self.assertEqual(assessment['individual_risks']['flood'], 0)
        self.assertEqual(assessment['individual_risks']['storm_surge'], 0)
        self.assertEqual(assessment['individual_risks']['cyclone_proximity'], 0)
        self.assertEqual(assessment['cyclone_feed_status'], 'available')
        self.assertEqual(assessment['data_source'], 'Open-Meteo (live model data)')
        self.assertEqual(assessment['country'], 'IN')
        self.assertIsNotNone(assessment['cyclone_feed_checked_at'])

    def test_nearest_active_cyclone_is_used_for_proximity_score(self):
        weather = {
            'city': 'Mumbai',
            'lat': 19.076,
            'lon': 72.8777,
            'wind_speed': 2.4,
            'wind_speed_unit': 'km/h',
            'rainfall': 0,
            'pressure': 1014.1,
            'source': 'Open-Meteo (live model data)',
        }
        cyclones = [
            {'identifier': 'far', 'lat': 5.0, 'lon': 80.0},
            {'identifier': 'near', 'lat': 19.5, 'lon': 72.9},
        ]
        with patch('Backend.routes.risk_routes.weather_service.get_current_weather', return_value=weather), \
             patch('Backend.routes.risk_routes.cyclone_service.get_active_cyclones', return_value={
                 'cyclones': cyclones, 'status': 200
             }):
            response = self.client.get('/api/risk/assessment?city=Mumbai')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['data']['individual_risks']['cyclone_proximity'],
            95
        )

    def test_missing_weather_measurements_are_not_reported_as_zero(self):
        from Backend.services.risk_service import RiskAssessmentService

        assessment = RiskAssessmentService().assess_risk(
            'Indore',
            {'source': 'Unknown provider', 'wind_speed': 10, 'rainfall': None}
        )

        self.assertIsNone(assessment['overall_score'])
        self.assertIsNone(assessment['individual_risks']['wind'])
        self.assertIsNone(assessment['individual_risks']['rainfall'])
        self.assertIsNone(assessment['individual_risks']['flood'])
        self.assertEqual(assessment['risk_level'], 'Unavailable')

    def test_storm_surge_is_not_reported_as_zero_for_unlisted_locations(self):
        from Backend.services.risk_service import RiskAssessmentService

        assessment = RiskAssessmentService().assess_risk(
            'Bogota',
            {
                'country': 'CO',
                'wind_speed': 5,
                'rainfall': 0,
                'pressure': 1015,
                'source': 'Open-Meteo (live model data)',
            },
            {'no_active_cyclones': True, 'feed_checked': True}
        )

        self.assertEqual(assessment['country'], 'CO')
        self.assertIsNone(assessment['individual_risks']['storm_surge'])


class TestSettingsEndpoints(unittest.TestCase):
    """Test settings endpoints."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_favorites(self):
        """Test getting favorite cities."""
        response = self.client.get('/api/settings/favorites')
        self.assertEqual(response.status_code, 200)

    def test_get_search_history(self):
        """Test getting search history."""
        response = self.client.get('/api/settings/search-history')
        self.assertEqual(response.status_code, 200)

    def test_get_config(self):
        """Test getting app configuration."""
        response = self.client.get('/api/settings/config')
        self.assertEqual(response.status_code, 200)


class TestDatabaseModels(unittest.TestCase):
    """Test database models."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.config.from_object(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_city(self):
        """Test creating a city record."""
        city = City(name='Indore', country='IN', lat=22.7196, lon=75.8577)
        db.session.add(city)
        db.session.commit()
        self.assertIsNotNone(city.id)
        self.assertEqual(city.name, 'Indore')

    def test_city_favorite(self):
        """Test city favorite toggle."""
        city = City(name='Mumbai', country='IN', lat=19.0760, lon=72.8777, is_favorite=True)
        db.session.add(city)
        db.session.commit()
        self.assertTrue(city.is_favorite)

    def test_create_weather_observation(self):
        """Test creating a weather observation."""
        city = City(name='Delhi', country='IN', lat=28.6139, lon=77.2090)
        db.session.add(city)
        db.session.commit()

        obs = WeatherObservation(
            city_id=city.id,
            temperature=32.5,
            feels_like=35.0,
            temp_min=30.0,
            temp_max=35.0,
            humidity=65,
            pressure=1012,
            wind_speed=3.5,
            wind_deg=225,
            clouds=40,
            visibility=10000,
            weather_main='Clouds',
            weather_description='scattered clouds',
            observed_at=datetime.utcnow()
        )
        db.session.add(obs)
        db.session.commit()
        self.assertIsNotNone(obs.id)
        self.assertEqual(obs.temperature, 32.5)

    def test_create_weather_alert(self):
        """Test creating a weather alert."""
        alert = WeatherAlert(
            alert_type='heavy_rainfall',
            severity='warning',
            title='Heavy Rainfall Expected',
            description='Heavy rainfall expected in the next 24 hours.',
            affected_area='Mumbai, Maharashtra',
            recommended_action='Avoid low-lying areas',
            issued_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(hours=24)
        )
        db.session.add(alert)
        db.session.commit()
        self.assertIsNotNone(alert.id)
        self.assertEqual(alert.severity, 'warning')

    def test_create_cyclone(self):
        """Test creating a cyclone record."""
        cyclone = Cyclone(
            name='AMPHAN',
            identifier='IO012020',
            category='Super Cyclonic Storm',
            intensity='Very Severe',
            lat=15.5,
            lon=88.2,
            movement_dir='NNW',
            movement_speed=15.0,
            max_wind_speed=240,
            basin='NIO',
            status='active',
            source='IMD'
        )
        db.session.add(cyclone)
        db.session.commit()
        self.assertIsNotNone(cyclone.id)
        self.assertEqual(cyclone.name, 'AMPHAN')

    def test_search_history(self):
        """Test search history recording."""
        entry = SearchHistory(city_name='Pune', country='IN')
        db.session.add(entry)
        db.session.commit()
        self.assertIsNotNone(entry.id)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_import_utils(self):
        """Test that utils module can be imported."""
        from utils import format_wind_direction, haversine_distance, validate_city_name
        self.assertTrue(callable(format_wind_direction))

    def test_wind_direction(self):
        """Test wind direction formatting."""
        from utils import format_wind_direction
        self.assertEqual(format_wind_direction(0), 'N')
        self.assertEqual(format_wind_direction(90), 'E')
        self.assertEqual(format_wind_direction(180), 'S')
        self.assertEqual(format_wind_direction(270), 'W')

    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        from utils import haversine_distance
        # Distance from Delhi to Mumbai is approximately 1148 km
        distance = haversine_distance(28.6139, 77.2090, 19.0760, 72.8777)
        self.assertAlmostEqual(distance, 1148, delta=50)

    def test_validate_city_name(self):
        """Test city name validation."""
        from utils import validate_city_name
        self.assertTrue(validate_city_name('Indore'))
        self.assertTrue(validate_city_name('New Delhi'))
        self.assertTrue(validate_city_name('Buenos Aires, Argentina'))
        self.assertFalse(validate_city_name(''))
        self.assertFalse(validate_city_name('   '))

    def test_format_temperature(self):
        """Test temperature formatting."""
        from utils import format_temperature
        self.assertEqual(format_temperature(32.567), '32.6°C')
        self.assertEqual(format_temperature(32.567, 'fahrenheit'), '90.6°F')


if __name__ == '__main__':
    unittest.main()
