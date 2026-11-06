"""
WeatherPredictor – Machine learning forecasting, anomaly detection, and evaluation.

Uses Scikit-learn to train models on historical weather observations.
Features chronological train/test splits, real evaluation metrics (MAE, RMSE, R²),
and explicit handling of data sufficiency.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from sklearn.linear_model import Ridge, LinearRegression
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from Backend.models import db, City, WeatherObservation, HistoricalWeather

logger = logging.getLogger(__name__)


class WeatherPredictor:
    """Predictive modeling and anomaly detection for weather observations."""

    MIN_RECORDS_FOR_TRAINING = 50

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.metrics = {}

    def _fetch_observations(self, city_name, limit=500):
        """Fetch observations for a city ordered by time."""
        city = City.query.filter(City.name.ilike(city_name)).first()
        if not city:
            return None, []

        observations = (
            WeatherObservation.query.filter(
                WeatherObservation.city_id == city.id,
                WeatherObservation.source.in_([
                    'Open-Meteo (live model data)',
                    'Open-Meteo archive (reanalysis)',
                ]),
                WeatherObservation.observed_at.isnot(None),
            )
            .order_by(WeatherObservation.observed_at.asc(), WeatherObservation.id.desc())
            .limit(limit * 3)
            .all()
        )
        distinct_observations = {}
        for observation in observations:
            distinct_observations.setdefault(observation.observed_at, observation)
        return city, list(distinct_observations.values())[:limit]

    def _chronological_split(self, X, y, test_ratio=0.2):
        """Perform a chronological (non-shuffled) train/test split."""
        split_idx = int(len(X) * (1 - test_ratio))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        return X_train, X_test, y_train, y_test

    def train_temperature_model(self, city_name):
        """
        Train a temperature forecasting model using historical observations.

        Features: hour, day_of_year, month, humidity, pressure, wind_speed, clouds
        Target: temperature
        """
        city, obs = self._fetch_observations(city_name)
        if not city:
            return {
                'status': 'error',
                'message': f"City '{city_name}' not found in database.",
                'sufficient_data': False
            }

        if len(obs) < self.MIN_RECORDS_FOR_TRAINING:
            return {
                'status': 'insufficient_data',
                'message': (
                    f"Insufficient historical data for reliable predictions. "
                    f"Found {len(obs)} observations; at least {self.MIN_RECORDS_FOR_TRAINING} "
                    f"needed to avoid overfitted or unverified models."
                ),
                'current_records': len(obs),
                'required_records': self.MIN_RECORDS_FOR_TRAINING,
                'sufficient_data': False
            }

        # Build feature matrix
        data = []
        for o in obs:
            dt = o.observed_at or o.created_at
            data.append({
                'hour': dt.hour,
                'day_of_year': dt.timetuple().tm_yday,
                'month': dt.month,
                'humidity': o.humidity or 50.0,
                'pressure': o.pressure or 1013.0,
                'wind_speed': o.wind_speed or 2.0,
                'clouds': o.clouds or 0,
                'temperature': o.temperature,
                'source': o.source
            })

        df = pd.DataFrame(data).dropna()
        if len(df) < self.MIN_RECORDS_FOR_TRAINING:
            return {
                'status': 'insufficient_data',
                'message': "Insufficient clean records after removing null values.",
                'sufficient_data': False,
                'training_observations': len(df)
            }

        feature_cols = ['hour', 'day_of_year', 'month', 'humidity', 'pressure', 'wind_speed', 'clouds']
        X = df[feature_cols].values
        y = df['temperature'].values

        X_train, X_test, y_train, y_test = self._chronological_split(X, y, test_ratio=0.2)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)

        y_pred = model.predict(X_test_scaled)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        model_key = f"temp_{city.id}"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self.metrics[model_key] = {
            'mae': round(mae, 3),
            'rmse': round(rmse, 3),
            'r2': round(r2, 3),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'trained_at': datetime.now(timezone.utc).isoformat(),
            'model_type': 'Ridge Regression with StandardScaler'
        }

        return {
            'status': 'success',
            'city': city.name,
            'metrics': self.metrics[model_key],
            'sufficient_data': True,
            'feature_names': feature_cols,
            'training_observations': len(df),
            'training_data_sources': sorted(df['source'].unique().tolist())
        }

    def predict_temperature(self, city_name, hours_ahead=24):
        """Generate temperature prediction for the next N hours."""
        city, obs = self._fetch_observations(city_name)
        if not city or len(obs) < self.MIN_RECORDS_FOR_TRAINING:
            return {
                'status': 'insufficient_data',
                'message': (
                    f"Insufficient historical data for '{city_name}'. "
                    f"Available: {len(obs) if obs else 0} / {self.MIN_RECORDS_FOR_TRAINING} required. "
                    f"Prediction module requires more real observations."
                ),
                'sufficient_data': False,
                'predictions': [],
                'training_observations': len(obs) if obs else 0
            }

        model_key = f"temp_{city.id}"
        if model_key not in self.models:
            train_res = self.train_temperature_model(city_name)
            if not train_res.get('sufficient_data'):
                return train_res

        model = self.models[model_key]
        scaler = self.scalers[model_key]

        last_obs = obs[-1]
        base_time = last_obs.observed_at or datetime.now(timezone.utc)
        predictions = []

        for h in range(1, hours_ahead + 1):
            future_dt = base_time + timedelta(hours=h)
            feat = np.array([[
                future_dt.hour,
                future_dt.timetuple().tm_yday,
                future_dt.month,
                last_obs.humidity or 50.0,
                last_obs.pressure or 1013.0,
                last_obs.wind_speed or 2.0,
                last_obs.clouds or 0
            ]])
            scaled_feat = scaler.transform(feat)
            pred_temp = float(model.predict(scaled_feat)[0])

            predictions.append({
                'timestamp': future_dt.isoformat(),
                'hour_offset': h,
                'predicted_temperature': round(pred_temp, 2),
                'unit': '°C'
            })

        return {
            'status': 'success',
            'city': city.name,
            'hours_ahead': hours_ahead,
            'predictions': predictions,
            'metrics': self.metrics.get(model_key, {}),
            'sufficient_data': True,
            'methodology': 'Ridge Regression with chronological time-series validation',
            'training_observations': len(obs),
            'training_data_sources': sorted({observation.source for observation in obs})
        }

    def detect_anomalies(self, city_name):
        """Use Isolation Forest to detect anomalous weather observations."""
        city, obs = self._fetch_observations(city_name, limit=300)
        if not city or len(obs) < 20:
            return {
                'status': 'insufficient_data',
                'message': f"Anomaly detection requires at least 20 recorded observations. Available: {len(obs) if obs else 0}.",
                'sufficient_data': False,
                'anomalies': [],
                'training_observations': len(obs) if obs else 0
            }

        data = []
        for o in obs:
            data.append({
                'id': o.id,
                'observed_at': (o.observed_at or o.created_at).isoformat(),
                'temperature': o.temperature or 25.0,
                'humidity': o.humidity or 50.0,
                'pressure': o.pressure or 1013.0,
                'wind_speed': o.wind_speed or 0.0
            })

        df = pd.DataFrame(data)
        features = ['temperature', 'humidity', 'pressure', 'wind_speed']
        X = df[features].values

        iso = IsolationForest(contamination=0.05, random_state=42)
        preds = iso.fit_predict(X)

        anomalies = []
        for idx, p in enumerate(preds):
            if p == -1:  # Outlier
                anomalies.append({
                    'observation_id': int(df.iloc[idx]['id']),
                    'observed_at': df.iloc[idx]['observed_at'],
                    'temperature': float(df.iloc[idx]['temperature']),
                    'humidity': float(df.iloc[idx]['humidity']),
                    'pressure': float(df.iloc[idx]['pressure']),
                    'wind_speed': float(df.iloc[idx]['wind_speed']),
                    'anomaly_score': float(iso.score_samples(X[idx:idx+1])[0])
                })

        return {
            'status': 'success',
            'city': city.name,
            'total_inspected': len(df),
            'anomalies_detected': len(anomalies),
            'anomalies': anomalies,
            'sufficient_data': True,
            'algorithm': 'Isolation Forest (contamination=0.05)',
            'training_observations': len(df),
            'training_data_sources': sorted({observation.source for observation in obs})
        }

    def get_model_metrics(self, city_name):
        """Retrieve stored evaluation metrics for a city's model."""
        city = City.query.filter(City.name.ilike(city_name)).first()
        if not city:
            return {'status': 'error', 'message': f"City '{city_name}' not found."}

        model_key = f"temp_{city.id}"
        if model_key in self.metrics:
            return {
                'status': 'success',
                'city': city.name,
                'metrics': self.metrics[model_key]
            }

        # Attempt to train to get metrics
        train_res = self.train_temperature_model(city_name)
        return train_res
