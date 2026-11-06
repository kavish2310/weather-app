"""
SQLAlchemy database models for the Weather Intelligence & Cyclone Monitoring System.

Defines all tables: City, WeatherObservation, WeatherForecast, Cyclone,
CycloneTrackPoint, WeatherAlert, SearchHistory, HistoricalWeather.
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class City(db.Model):
    """Represents a city that users search for or have favorited."""

    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    country = db.Column(db.String(64), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    observations = db.relationship(
        'WeatherObservation', backref='city', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    forecasts = db.relationship(
        'WeatherForecast', backref='city', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    alerts = db.relationship(
        'WeatherAlert', backref='city', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    historical_records = db.relationship(
        'HistoricalWeather', backref='city', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        db.UniqueConstraint('name', 'country', name='uq_city_name_country'),
    )

    def to_dict(self):
        """Serialize city to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'country': self.country,
            'lat': self.lat,
            'lon': self.lon,
            'is_favorite': self.is_favorite,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<City {self.name}, {self.country}>'


class WeatherObservation(db.Model):
    """Stores a single current-weather observation for a city."""

    __tablename__ = 'weather_observations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_id = db.Column(
        db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True
    )
    temperature = db.Column(db.Float, nullable=True)
    feels_like = db.Column(db.Float, nullable=True)
    temp_min = db.Column(db.Float, nullable=True)
    temp_max = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Integer, nullable=True)
    pressure = db.Column(db.Integer, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    wind_deg = db.Column(db.Integer, nullable=True)
    rainfall = db.Column(db.Float, nullable=True, default=0.0)
    clouds = db.Column(db.Integer, nullable=True)
    visibility = db.Column(db.Integer, nullable=True)
    uv_index = db.Column(db.Float, nullable=True)
    sunrise = db.Column(db.DateTime, nullable=True)
    sunset = db.Column(db.DateTime, nullable=True)
    weather_main = db.Column(db.String(64), nullable=True)
    weather_description = db.Column(db.String(256), nullable=True)
    weather_icon = db.Column(db.String(16), nullable=True)
    source = db.Column(db.String(64), nullable=True)
    air_quality_index = db.Column(db.Integer, nullable=True)
    observed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """Serialize observation to dictionary."""
        return {
            'id': self.id,
            'city_id': self.city_id,
            'temperature': self.temperature,
            'feels_like': self.feels_like,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'wind_speed': self.wind_speed,
            'wind_deg': self.wind_deg,
            'rainfall': self.rainfall,
            'clouds': self.clouds,
            'visibility': self.visibility,
            'uv_index': self.uv_index,
            'sunrise': self.sunrise.isoformat() if self.sunrise else None,
            'sunset': self.sunset.isoformat() if self.sunset else None,
            'weather_main': self.weather_main,
            'weather_description': self.weather_description,
            'weather_icon': self.weather_icon,
            'source': self.source,
            'air_quality_index': self.air_quality_index,
            'observed_at': self.observed_at.isoformat() if self.observed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<WeatherObservation city_id={self.city_id} temp={self.temperature}>'


class WeatherForecast(db.Model):
    """Stores a single forecast data point for a city."""

    __tablename__ = 'weather_forecasts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_id = db.Column(
        db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True
    )
    forecast_dt = db.Column(db.DateTime, nullable=False)
    temperature = db.Column(db.Float, nullable=True)
    feels_like = db.Column(db.Float, nullable=True)
    temp_min = db.Column(db.Float, nullable=True)
    temp_max = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Integer, nullable=True)
    pressure = db.Column(db.Integer, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    wind_deg = db.Column(db.Integer, nullable=True)
    rainfall_prob = db.Column(db.Float, nullable=True)
    rainfall_amount = db.Column(db.Float, nullable=True, default=0.0)
    clouds = db.Column(db.Integer, nullable=True)
    weather_main = db.Column(db.String(64), nullable=True)
    weather_description = db.Column(db.String(256), nullable=True)
    weather_icon = db.Column(db.String(16), nullable=True)
    source = db.Column(db.String(64), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """Serialize forecast to dictionary."""
        return {
            'id': self.id,
            'city_id': self.city_id,
            'forecast_dt': self.forecast_dt.isoformat() if self.forecast_dt else None,
            'temperature': self.temperature,
            'feels_like': self.feels_like,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'wind_speed': self.wind_speed,
            'wind_deg': self.wind_deg,
            'rainfall_prob': self.rainfall_prob,
            'rainfall_amount': self.rainfall_amount,
            'clouds': self.clouds,
            'weather_main': self.weather_main,
            'weather_description': self.weather_description,
            'weather_icon': self.weather_icon,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<WeatherForecast city_id={self.city_id} dt={self.forecast_dt}>'


class Cyclone(db.Model):
    """Represents an active or historical tropical cyclone."""

    __tablename__ = 'cyclones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=True)
    identifier = db.Column(db.String(64), nullable=True, unique=True, index=True)
    category = db.Column(db.String(32), nullable=True)
    intensity = db.Column(db.String(64), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    movement_dir = db.Column(db.String(32), nullable=True)
    movement_speed = db.Column(db.Float, nullable=True)
    central_pressure = db.Column(db.Float, nullable=True)
    max_wind_speed = db.Column(db.Float, nullable=True)
    basin = db.Column(db.String(32), nullable=True)
    status = db.Column(db.String(32), default='active', nullable=False)
    source = db.Column(db.String(64), nullable=True)
    first_detected = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    track_points = db.relationship(
        'CycloneTrackPoint', backref='cyclone', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        """Serialize cyclone to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'identifier': self.identifier,
            'category': self.category,
            'intensity': self.intensity,
            'lat': self.lat,
            'lon': self.lon,
            'movement_dir': self.movement_dir,
            'movement_speed': self.movement_speed,
            'central_pressure': self.central_pressure,
            'max_wind_speed': self.max_wind_speed,
            'basin': self.basin,
            'status': self.status,
            'source': self.source,
            'first_detected': self.first_detected.isoformat() if self.first_detected else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self):
        return f'<Cyclone {self.name} ({self.identifier})>'


class CycloneTrackPoint(db.Model):
    """A single position/time point along a cyclone's track."""

    __tablename__ = 'cyclone_track_points'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cyclone_id = db.Column(
        db.Integer, db.ForeignKey('cyclones.id', ondelete='CASCADE'), nullable=False, index=True
    )
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    pressure = db.Column(db.Float, nullable=True)
    category = db.Column(db.String(32), nullable=True)
    is_forecast = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """Serialize track point to dictionary."""
        return {
            'id': self.id,
            'cyclone_id': self.cyclone_id,
            'lat': self.lat,
            'lon': self.lon,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'wind_speed': self.wind_speed,
            'pressure': self.pressure,
            'category': self.category,
            'is_forecast': self.is_forecast,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<CycloneTrackPoint cyclone_id={self.cyclone_id} ({self.lat}, {self.lon})>'


class WeatherAlert(db.Model):
    """Weather alert or warning, possibly tied to a city."""

    __tablename__ = 'weather_alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_id = db.Column(
        db.Integer, db.ForeignKey('cities.id', ondelete='SET NULL'), nullable=True, index=True
    )
    alert_type = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(32), nullable=False, default='moderate')
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    issuing_authority = db.Column(db.String(128), nullable=True)
    issued_at = db.Column(db.DateTime, nullable=True)
    valid_until = db.Column(db.DateTime, nullable=True)
    affected_area = db.Column(db.String(512), nullable=True)
    recommended_action = db.Column(db.Text, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """Serialize alert to dictionary."""
        return {
            'id': self.id,
            'city_id': self.city_id,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'issuing_authority': self.issuing_authority,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'affected_area': self.affected_area,
            'recommended_action': self.recommended_action,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<WeatherAlert {self.title} severity={self.severity}>'


class SearchHistory(db.Model):
    """Records every city search performed by users."""

    __tablename__ = 'search_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_name = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(64), nullable=True)
    searched_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        """Serialize search record to dictionary."""
        return {
            'id': self.id,
            'city_name': self.city_name,
            'country': self.country,
            'searched_at': self.searched_at.isoformat() if self.searched_at else None,
        }

    def __repr__(self):
        return f'<SearchHistory {self.city_name}>'


class HistoricalWeather(db.Model):
    """Daily aggregated historical weather data for trend analysis and ML training."""

    __tablename__ = 'historical_weather'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_id = db.Column(
        db.Integer, db.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False)
    temp_avg = db.Column(db.Float, nullable=True)
    temp_min = db.Column(db.Float, nullable=True)
    temp_max = db.Column(db.Float, nullable=True)
    humidity_avg = db.Column(db.Float, nullable=True)
    rainfall = db.Column(db.Float, nullable=True, default=0.0)
    wind_speed_avg = db.Column(db.Float, nullable=True)
    pressure_avg = db.Column(db.Float, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        db.UniqueConstraint('city_id', 'date', name='uq_city_date'),
    )

    def to_dict(self):
        """Serialize historical record to dictionary."""
        return {
            'id': self.id,
            'city_id': self.city_id,
            'date': self.date.isoformat() if self.date else None,
            'temp_avg': self.temp_avg,
            'temp_min': self.temp_min,
            'temp_max': self.temp_max,
            'humidity_avg': self.humidity_avg,
            'rainfall': self.rainfall,
            'wind_speed_avg': self.wind_speed_avg,
            'pressure_avg': self.pressure_avg,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<HistoricalWeather city_id={self.city_id} date={self.date}>'
