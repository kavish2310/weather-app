"""
RiskAssessmentService – computes multi-factor risk scores for weather hazards.

Considers wind, rainfall, flooding, storm surge, and cyclone proximity to
produce an overall risk score (0-100) with recommendations.
"""

import logging

from Backend.utils import haversine_distance

logger = logging.getLogger(__name__)

# Known coastal cities for storm-surge relevance
COASTAL_CITIES = {
    'mumbai', 'chennai', 'kolkata', 'visakhapatnam', 'bhubaneswar',
    'kochi', 'mangalore', 'goa', 'puri', 'paradip', 'tuticorin',
    'pondicherry', 'machilipatnam', 'kakinada', 'surat', 'porbandar',
    'miami', 'houston', 'new orleans', 'tampa', 'jacksonville',
    'galveston', 'corpus christi', 'mobile', 'pensacola', 'key west',
    'havana', 'manila', 'hong kong', 'shanghai', 'tokyo', 'osaka',
    'darwin', 'cairns', 'dhaka', 'chittagong', 'yangon', 'cox\'s bazar',
    'maputo', 'dar es salaam', 'mombasa', 'durban',
}


class RiskAssessmentService:
    """Produces risk assessments based on weather observations and cyclone data."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess_risk(self, city, weather_data, cyclone_data=None):
        """
        Comprehensive risk assessment for a city given current conditions.

        Args:
            city (str): City name.
            weather_data (dict): Current weather observation dict.
            cyclone_data (dict | None): Active cyclone dict (optional).

        Returns:
            dict: Full risk assessment with scores, level, recommendations.
        """
        wind_speed = weather_data.get('wind_speed', 0) or 0
        rainfall = weather_data.get('rainfall', 0) or 0
        pressure = weather_data.get('pressure', 1013) or 1013
        humidity = weather_data.get('humidity', 0) or 0
        visibility = weather_data.get('visibility', 10000) or 10000
        temperature = weather_data.get('temperature', 25) or 25

        # Convert OWM wind speed (m/s) to km/h for risk calculations
        wind_speed_kmh = wind_speed * 3.6

        wind_risk = self.calculate_wind_risk(wind_speed_kmh)
        rainfall_risk = self.calculate_rainfall_risk(rainfall)
        flood_risk = self.calculate_flood_risk(rainfall, duration_hours=1)
        is_coastal = self._is_coastal_city(city)
        storm_surge_risk = self.calculate_storm_surge_risk(
            wind_speed_kmh, pressure, is_coastal
        )

        individual_risks = {
            'wind': wind_risk,
            'rainfall': rainfall_risk,
            'flood': flood_risk,
            'storm_surge': storm_surge_risk,
        }

        # Extra risk from nearby cyclone
        cyclone_proximity_risk = 0
        if cyclone_data and cyclone_data.get('lat') and cyclone_data.get('lon'):
            city_lat = weather_data.get('lat')
            city_lon = weather_data.get('lon')
            if city_lat and city_lon:
                dist = haversine_distance(
                    cyclone_data['lat'], cyclone_data['lon'],
                    city_lat, city_lon,
                )
                if dist < 100:
                    cyclone_proximity_risk = 95
                elif dist < 300:
                    cyclone_proximity_risk = 70
                elif dist < 500:
                    cyclone_proximity_risk = 45
                elif dist < 1000:
                    cyclone_proximity_risk = 20
                individual_risks['cyclone_proximity'] = cyclone_proximity_risk

        overall_score = self.calculate_overall_risk(individual_risks)
        risk_level = self.get_risk_level(overall_score)

        contributing = []
        for factor, score in individual_risks.items():
            if score >= 30:
                contributing.append({
                    'factor': factor,
                    'score': score,
                    'level': self.get_risk_level(score),
                })
        contributing.sort(key=lambda x: x['score'], reverse=True)

        recommendations = self.get_recommendations(risk_level, individual_risks)

        return {
            'city': city,
            'overall_score': overall_score,
            'risk_level': risk_level,
            'individual_risks': individual_risks,
            'contributing_factors': contributing,
            'recommendations': recommendations,
            'is_coastal': is_coastal,
            'weather_summary': {
                'wind_speed_kmh': round(wind_speed_kmh, 1),
                'rainfall_mm': rainfall,
                'pressure_hpa': pressure,
                'humidity_pct': humidity,
                'visibility_m': visibility,
                'temperature_c': temperature,
            },
            'methodology': (
                'Risk scores (0-100) are computed from Beaufort-scale wind thresholds, '
                'IMD/WMO rainfall intensity categories, hydrological flood estimates, '
                'and coastal storm-surge potential. Cyclone proximity adds an additional '
                'distance-weighted factor.'
            ),
            'limitations': (
                'This assessment uses simplified models and may not account for local '
                'topography, drainage infrastructure, or real-time tidal conditions. '
                'Always follow official government and meteorological advisories.'
            ),
            'status': 200,
        }

    # ------------------------------------------------------------------
    # Individual risk calculators
    # ------------------------------------------------------------------

    def calculate_wind_risk(self, wind_speed_kmh):
        """
        Score wind risk (0-100) based on the Beaufort scale.

        Args:
            wind_speed_kmh (float): Wind speed in km/h.

        Returns:
            int: Risk score 0-100.
        """
        if wind_speed_kmh < 20:
            return 0
        if wind_speed_kmh < 40:
            return 15
        if wind_speed_kmh < 60:
            return 30
        if wind_speed_kmh < 90:
            return 50
        if wind_speed_kmh < 120:
            return 70
        if wind_speed_kmh < 160:
            return 85
        return 100

    def calculate_rainfall_risk(self, rainfall_mm):
        """
        Score rainfall risk (0-100) based on mm of rain in 1 hour.

        Uses IMD intensity categories.

        Args:
            rainfall_mm (float): Rainfall in mm (1 h).

        Returns:
            int: Risk score 0-100.
        """
        if rainfall_mm < 2.5:
            return 0
        if rainfall_mm < 7.5:
            return 15
        if rainfall_mm < 35:
            return 35
        if rainfall_mm < 65:
            return 55
        if rainfall_mm < 125:
            return 75
        return 95

    def calculate_flood_risk(self, rainfall_mm, duration_hours=1):
        """
        Estimate flood risk considering cumulative rainfall over a duration.

        Args:
            rainfall_mm (float): Total rainfall in mm.
            duration_hours (float): Observation period in hours.

        Returns:
            int: Risk score 0-100.
        """
        if duration_hours <= 0:
            duration_hours = 1
        rate_mm_per_hour = rainfall_mm / duration_hours

        if rate_mm_per_hour < 5:
            base = 0
        elif rate_mm_per_hour < 15:
            base = 20
        elif rate_mm_per_hour < 30:
            base = 40
        elif rate_mm_per_hour < 65:
            base = 65
        else:
            base = 90

        # Sustained rainfall amplifies flood risk
        if duration_hours > 6 and base > 0:
            base = min(100, base + 10)
        if duration_hours > 12 and base > 0:
            base = min(100, base + 10)

        return base

    def calculate_storm_surge_risk(self, wind_speed_kmh, pressure_hpa, is_coastal):
        """
        Estimate storm surge risk for a coastal location.

        Non-coastal cities automatically score 0.

        Args:
            wind_speed_kmh (float): Wind speed in km/h.
            pressure_hpa (float): Sea-level pressure in hPa.
            is_coastal (bool): Whether the city is coastal.

        Returns:
            int: Risk score 0-100.
        """
        if not is_coastal:
            return 0

        score = 0
        # Wind contribution
        if wind_speed_kmh >= 120:
            score += 50
        elif wind_speed_kmh >= 90:
            score += 35
        elif wind_speed_kmh >= 60:
            score += 20
        elif wind_speed_kmh >= 40:
            score += 10

        # Low pressure contribution (< 1000 hPa is significant)
        if pressure_hpa < 950:
            score += 50
        elif pressure_hpa < 970:
            score += 35
        elif pressure_hpa < 990:
            score += 20
        elif pressure_hpa < 1000:
            score += 10

        return min(100, score)

    def calculate_overall_risk(self, individual_risks):
        """
        Compute a weighted-average overall risk score.

        Weights: wind=0.30, rainfall=0.25, flood=0.20, storm_surge=0.15,
        cyclone_proximity=0.10.

        Args:
            individual_risks (dict): Mapping of risk factor -> score.

        Returns:
            int: Overall risk score 0-100.
        """
        weights = {
            'wind': 0.30,
            'rainfall': 0.25,
            'flood': 0.20,
            'storm_surge': 0.15,
            'cyclone_proximity': 0.10,
        }
        total_weight = 0.0
        weighted_sum = 0.0
        for factor, score in individual_risks.items():
            w = weights.get(factor, 0.1)
            weighted_sum += score * w
            total_weight += w

        if total_weight == 0:
            return 0
        return round(weighted_sum / total_weight)

    def get_risk_level(self, score):
        """
        Map a numeric risk score to a human-readable level.

        Args:
            score (int): 0-100 risk score.

        Returns:
            str: 'Low', 'Moderate', 'High', or 'Extreme'.
        """
        if score < 25:
            return 'Low'
        if score < 50:
            return 'Moderate'
        if score < 75:
            return 'High'
        return 'Extreme'

    def get_recommendations(self, risk_level, risk_factors):
        """
        Generate safety recommendations based on risk level and contributing factors.

        Args:
            risk_level (str): Overall risk level string.
            risk_factors (dict): Individual risk scores.

        Returns:
            list[str]: Human-readable safety recommendations.
        """
        recs = []

        if risk_level == 'Low':
            recs.append('No significant weather hazards at this time.')
            recs.append('Stay updated with the latest weather forecasts.')
            return recs

        if risk_level in ('Moderate', 'High', 'Extreme'):
            recs.append('Monitor official weather updates frequently.')

        # Wind-specific
        wind = risk_factors.get('wind', 0)
        if wind >= 70:
            recs.append('Seek sturdy shelter immediately. Avoid being outdoors.')
            recs.append('Secure or bring indoors any loose objects that could become projectiles.')
        elif wind >= 40:
            recs.append('Exercise caution outdoors; strong winds expected.')
            recs.append('Avoid driving high-profile vehicles.')

        # Rainfall / flood
        rainfall = risk_factors.get('rainfall', 0)
        flood = risk_factors.get('flood', 0)
        if rainfall >= 60 or flood >= 60:
            recs.append('Avoid low-lying areas and waterlogged roads.')
            recs.append('Keep an emergency kit ready with food, water, and medicines.')
            recs.append('Do not attempt to cross flooded streams or roads on foot or by vehicle.')
        elif rainfall >= 30 or flood >= 30:
            recs.append('Carry rain protection; localised waterlogging possible.')

        # Storm surge
        surge = risk_factors.get('storm_surge', 0)
        if surge >= 50:
            recs.append('If in a coastal area, move to higher ground immediately.')
            recs.append('Follow evacuation orders from local authorities.')
        elif surge >= 25:
            recs.append('Coastal residents should remain alert for storm surge advisories.')

        # Cyclone proximity
        cyc = risk_factors.get('cyclone_proximity', 0)
        if cyc >= 70:
            recs.append('A tropical cyclone is nearby. Follow all official evacuation orders.')
            recs.append('Stock up on essentials; power outages are likely.')
        elif cyc >= 30:
            recs.append('A tropical cyclone is in the region. Stay prepared for rapid changes.')

        if risk_level == 'Extreme':
            recs.append('This is a life-threatening situation. Prioritise personal safety above all else.')

        return recs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_coastal_city(self, city_name):
        """
        Check whether a city is in the known coastal-city list.

        Args:
            city_name (str): City name.

        Returns:
            bool: True if coastal.
        """
        if not city_name:
            return False
        return city_name.strip().lower() in COASTAL_CITIES
