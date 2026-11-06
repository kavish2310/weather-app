"""
CycloneService – monitors and retrieves tropical cyclone data.

Sources: NOAA NHC RSS feeds, JTWC advisories, IMD bulletins.
Stores cyclone metadata and track-point histories in the database.
"""

import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from Backend.config import Config
from Backend.models import db, Cyclone, CycloneTrackPoint
from Backend.utils import safe_api_request, haversine_distance

logger = logging.getLogger(__name__)

# NOAA National Hurricane Center GIS RSS feeds
NHC_ATLANTIC_FEED = 'https://www.nhc.noaa.gov/gis-at.xml'
NHC_PACIFIC_FEED = 'https://www.nhc.noaa.gov/gis-ep.xml'
# IMD RSS/data feed
IMD_FEED_URL = 'https://mausam.imd.gov.in/backend/rss_cyclone.xml'
# JTWC data (public best-track / warning feed)
JTWC_FEED_URL = 'https://www.metoc.navy.mil/jtwc/rss/jtwc.rss'


class CycloneService:
    """Encapsulates cyclone data retrieval, parsing, and storage."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_active_cyclones(self):
        """
        Fetch active cyclone information from multiple authoritative sources.

        Returns:
            dict: {'cyclones': [...], 'sources_checked': [...], 'message': str, 'status': 200}
        """
        cyclones = []
        source_results = [
            ('NOAA NHC Atlantic', self._fetch_nhc_feed(NHC_ATLANTIC_FEED, basin='atlantic')),
            ('NOAA NHC Eastern Pacific', self._fetch_nhc_feed(NHC_PACIFIC_FEED, basin='east_pacific')),
            ('JTWC', self._fetch_jtwc_feed()),
            ('IMD India', self._fetch_imd_feed()),
        ]
        sources_checked = [name for name, result in source_results if result is not None]
        sources_unavailable = [name for name, result in source_results if result is None]
        for _, result in source_results:
            if result:
                cyclones.extend(result)

        cyclones = list({item['identifier']: item for item in cyclones if item.get('identifier')}.values())

        # Persist any new cyclones
        for cyc in cyclones:
            self._save_cyclone(cyc)

        all_sources_failed = not sources_checked
        message = (
            'Live cyclone feeds are unavailable; active conditions could not be confirmed.'
            if all_sources_failed
            else f'{len(cyclones)} active cyclone(s) detected.'
            if cyclones
            else 'No active cyclones reported by the available live sources.'
        )
        return {
            'cyclones': cyclones,
            'count': len(cyclones),
            'sources_checked': sources_checked,
            'sources_unavailable': sources_unavailable,
            'message': message,
            'status': 503 if all_sources_failed else 200,
        }

    def get_cyclone_track(self, cyclone_id):
        """
        Return the track-point history for a stored cyclone.

        Args:
            cyclone_id (int): Primary key of the Cyclone record.

        Returns:
            dict: Track-point list or error dict.
        """
        cyclone = db.session.get(Cyclone, cyclone_id)
        if not cyclone:
            return {'error': f'Cyclone with id {cyclone_id} not found', 'status': 404}

        points = (
            CycloneTrackPoint.query
            .filter_by(cyclone_id=cyclone_id)
            .order_by(CycloneTrackPoint.timestamp.asc())
            .all()
        )
        return {
            'cyclone': cyclone.to_dict(),
            'track_points': [p.to_dict() for p in points],
            'status': 200,
        }

    def get_affected_regions(self, cyclone_id):
        """
        Estimate coastal / land regions potentially affected by a cyclone.

        Uses the cyclone's current position plus movement direction to project
        a crude 500 km impact radius.

        Args:
            cyclone_id (int): Cyclone primary key.

        Returns:
            dict: Affected regions list or error dict.
        """
        cyclone = db.session.get(Cyclone, cyclone_id)
        if not cyclone:
            return {'error': f'Cyclone with id {cyclone_id} not found', 'status': 404}

        # Known major coastal cities (name, lat, lon, country)
        coastal_cities = [
            ('Mumbai', 19.076, 72.8777, 'India'),
            ('Chennai', 13.0827, 80.2707, 'India'),
            ('Kolkata', 22.5726, 88.3639, 'India'),
            ('Visakhapatnam', 17.6868, 83.2185, 'India'),
            ('Bhubaneswar', 20.2961, 85.8245, 'India'),
            ('Dhaka', 23.8103, 90.4125, 'Bangladesh'),
            ('Chittagong', 22.3569, 91.7832, 'Bangladesh'),
            ('Yangon', 16.8661, 96.1951, 'Myanmar'),
            ('Miami', 25.7617, -80.1918, 'USA'),
            ('Houston', 29.7604, -95.3698, 'USA'),
            ('New Orleans', 29.9511, -90.0715, 'USA'),
            ('Tampa', 27.9506, -82.4572, 'USA'),
            ('Havana', 23.1136, -82.3666, 'Cuba'),
            ('Manila', 14.5995, 120.9842, 'Philippines'),
            ('Tokyo', 35.6762, 139.6503, 'Japan'),
            ('Hong Kong', 22.3193, 114.1694, 'China'),
            ('Shanghai', 31.2304, 121.4737, 'China'),
            ('Darwin', -12.4634, 130.8456, 'Australia'),
            ('Maputo', -25.9692, 32.5732, 'Mozambique'),
            ('Dar es Salaam', -6.7924, 39.2083, 'Tanzania'),
        ]

        if cyclone.lat is None or cyclone.lon is None:
            return {
                'cyclone': cyclone.to_dict(),
                'affected_regions': [],
                'message': 'Cyclone position data unavailable for region estimation.',
                'status': 200,
            }

        impact_radius_km = 500.0
        affected = []
        for city_name, lat, lon, country in coastal_cities:
            dist = haversine_distance(cyclone.lat, cyclone.lon, lat, lon)
            if dist <= impact_radius_km:
                affected.append({
                    'city': city_name,
                    'country': country,
                    'distance_km': round(dist, 1),
                    'risk_level': 'High' if dist < 200 else 'Moderate',
                })

        affected.sort(key=lambda x: x['distance_km'])
        return {
            'cyclone': cyclone.to_dict(),
            'affected_regions': affected,
            'impact_radius_km': impact_radius_km,
            'status': 200,
        }

    def get_historical_cyclones(self, basin=None, year=None):
        """
        Retrieve stored historical cyclone records filtered by basin and/or year.

        Args:
            basin (str | None): Basin code (e.g. 'atlantic', 'east_pacific').
            year (int | None): Year of first detection.

        Returns:
            dict: List of cyclones or error dict.
        """
        query = Cyclone.query
        if basin:
            query = query.filter(Cyclone.basin == basin)
        if year:
            query = query.filter(
                db.extract('year', Cyclone.first_detected) == int(year)
            )
        cyclones = query.order_by(Cyclone.first_detected.desc()).all()
        return {
            'cyclones': [c.to_dict() for c in cyclones],
            'count': len(cyclones),
            'status': 200,
        }

    def estimate_arrival(self, cyclone_id, target_lat, target_lon):
        """
        Estimate how long until a cyclone reaches a target location.

        Uses great-circle distance and current movement speed.

        Args:
            cyclone_id (int): Cyclone primary key.
            target_lat (float): Target latitude.
            target_lon (float): Target longitude.

        Returns:
            dict: Estimated arrival hours, distance, or error dict.
        """
        cyclone = db.session.get(Cyclone, cyclone_id)
        if not cyclone:
            return {'error': f'Cyclone with id {cyclone_id} not found', 'status': 404}

        if cyclone.lat is None or cyclone.lon is None:
            return {'error': 'Cyclone position data unavailable', 'status': 400}

        distance_km = haversine_distance(cyclone.lat, cyclone.lon, target_lat, target_lon)

        speed_kmh = cyclone.movement_speed
        if not speed_kmh or speed_kmh <= 0:
            return {
                'cyclone': cyclone.to_dict(),
                'distance_km': round(distance_km, 1),
                'estimated_hours': None,
                'message': 'Movement speed data unavailable; cannot estimate arrival.',
                'status': 200,
            }

        estimated_hours = distance_km / speed_kmh

        return {
            'cyclone': cyclone.to_dict(),
            'target': {'lat': target_lat, 'lon': target_lon},
            'distance_km': round(distance_km, 1),
            'movement_speed_kmh': speed_kmh,
            'estimated_hours': round(estimated_hours, 1),
            'estimated_days': round(estimated_hours / 24, 2),
            'disclaimer': (
                'This is a rough straight-line estimate. Actual cyclone paths curve '
                'and change speed. Always follow official meteorological advisories.'
            ),
            'status': 200,
        }

    # ------------------------------------------------------------------
    # Feed fetchers
    # ------------------------------------------------------------------

    def _fetch_nhc_feed(self, feed_url, basin='atlantic'):
        """
        Fetch and parse a NOAA NHC GIS RSS feed.

        Args:
            feed_url (str): URL of the NHC RSS XML feed.
            basin (str): Basin label.

        Returns:
            list[dict]: Parsed cyclone dicts (may be empty).
        """
        try:
            import requests as req
            resp = req.get(feed_url, timeout=15)
            resp.raise_for_status()
            return self._parse_nhc_data(resp.text, basin)
        except Exception as exc:
            logger.warning('Failed to fetch NHC feed %s: %s', feed_url, exc)
            return None

    def _fetch_jtwc_feed(self):
        """
        Fetch and parse JTWC RSS feed for western-Pacific / Indian Ocean cyclones.

        Returns:
            list[dict]: Parsed cyclone dicts (may be empty).
        """
        try:
            import requests as req
            resp = req.get(JTWC_FEED_URL, timeout=15, headers={'User-Agent': 'WeatherIQ/2.0'})
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            cyclones = []
            for item in root.findall('./channel/item'):
                description = item.findtext('description', '')
                warning_links = re.findall(
                    r"""href=['"]([^'"]+\.txt)['"]""",
                    description,
                    re.IGNORECASE
                )
                for link in warning_links:
                    if not re.search(r'(?:web|warn)\.txt$', link, re.IGNORECASE):
                        continue
                    try:
                        warning = req.get(link, timeout=10, headers={'User-Agent': 'WeatherIQ/2.0'})
                        warning.raise_for_status()
                        parsed = self._parse_jtwc_warning(warning.text, link)
                        if parsed:
                            cyclones.append(parsed)
                    except req.exceptions.RequestException as exc:
                        logger.warning('Failed to fetch JTWC warning %s: %s', link, exc)
            return cyclones
        except Exception as exc:
            logger.warning('Failed to fetch JTWC feed: %s', exc)
            return None

    def _fetch_imd_feed(self):
        """
        Fetch and parse IMD cyclone bulletins.

        Returns:
            list[dict]: Parsed cyclone dicts (may be empty).
        """
        try:
            import requests as req
            resp = req.get(IMD_FEED_URL, timeout=15)
            resp.raise_for_status()
            return self._parse_imd_data(resp.text)
        except Exception as exc:
            logger.warning('Failed to fetch IMD feed: %s', exc)
            return None

    def _parse_jtwc_warning(self, text, warning_url):
        """Parse current position and intensity from an official JTWC warning."""
        subject = re.search(r'SUBJ/([^/\r\n]+?)(?:\s+WARNING\s+NR|\s+WARNING NR)', text, re.IGNORECASE)
        if not subject:
            return None

        name = subject.group(1).strip()
        position_block = re.search(r'WARNING POSITION:(.*?)(?:PRESENT WIND DISTRIBUTION:|REPEAT POSIT:)', text, re.IGNORECASE | re.DOTALL)
        position_text = position_block.group(1) if position_block else text
        lat, lon = self._extract_coords_from_description(position_text)
        if lat is None or lon is None:
            return None

        movement = re.search(
            r'MOVEMENT PAST SIX HOURS\s*-\s*(\d{1,3})\s+DEGREES\s+AT\s+([\d.]+)\s+KTS',
            text,
            re.IGNORECASE
        )
        wind = re.search(r'MAX SUSTAINED WINDS\s*-\s*([\d.]+)\s*KT', text, re.IGNORECASE)
        pressure = re.search(r'MINIMUM CENTRAL PRESSURE\s*-\s*([\d.]+)\s*MB', text, re.IGNORECASE)
        identifier_match = re.search(r'/([a-z]{2}\d{4})\w*\.txt$', warning_url, re.IGNORECASE)
        identifier = identifier_match.group(1).upper() if identifier_match else name.upper().replace(' ', '-')
        basin_code = identifier[:2].lower()
        basin = {
            'wp': 'west_pacific',
            'cp': 'central_pacific',
            'ep': 'east_pacific',
            'io': 'north_indian_ocean',
            'ni': 'north_indian_ocean',
            'sh': 'southern_hemisphere',
        }.get(basin_code, 'tropical_cyclone')
        return {
            'name': name,
            'identifier': f'JTWC-{identifier}',
            'category': self._extract_category_from_title(name),
            'intensity': self._extract_category_from_title(name),
            'lat': lat,
            'lon': lon,
            'movement_dir': f"{movement.group(1)}°" if movement else None,
            'movement_speed': round(float(movement.group(2)) * 1.852, 1) if movement else None,
            'central_pressure': float(pressure.group(1)) if pressure else None,
            'max_wind_speed': round(float(wind.group(1)) * 1.852, 1) if wind else None,
            'basin': basin,
            'status': 'active',
            'source': 'JTWC',
            'source_url': warning_url,
            'wind_speed_unit': 'km/h',
        }

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    def _parse_nhc_data(self, xml_data, basin='atlantic'):
        """
        Parse NOAA NHC RSS/XML data into cyclone dicts.

        The NHC GIS RSS feed contains <item> elements with cyclone advisories.

        Args:
            xml_data (str): Raw XML string.
            basin (str): Basin label.

        Returns:
            list[dict]: Cyclone dicts.
        """
        cyclones = []
        try:
            root = ET.fromstring(xml_data)
            channel = root.find('channel')
            if channel is None:
                return cyclones

            for item in channel.findall('item'):
                title = item.findtext('title', '')
                description = item.findtext('description', '')
                link = item.findtext('link', '')

                # Skip non-cyclone items, negative outlooks ("there are no tropical cyclones"), or routine updates
                lower_title = title.lower()
                if 'no tropical cyclone' in lower_title or 'there are no' in lower_title or 'calm' in lower_title:
                    continue

                is_cyclone_item = any(
                    kw in lower_title
                    for kw in ['hurricane', 'tropical storm', 'tropical depression', 'cyclonic storm', 'cyclone']
                )
                if not is_cyclone_item:
                    continue

                # Try to extract lat/lon from nhc:Cyclone element or description
                lat, lon = self._extract_coords_from_description(description)
                if lat is None or lon is None:
                    continue

                # Extract name from title (e.g. "Hurricane Milton Advisory ...")
                name_parts = title.split()
                name = ' '.join(name_parts[:3]) if len(name_parts) >= 3 else title

                cyclone_dict = {
                    'name': name,
                    'identifier': f'NHC-{basin}-{name.replace(" ", "-")}',
                    'category': self._extract_category_from_title(title),
                    'intensity': self._extract_category_from_title(title),
                    'lat': lat,
                    'lon': lon,
                    'movement_dir': None,
                    'movement_speed': None,
                    'central_pressure': None,
                    'max_wind_speed': None,
                    'basin': basin,
                    'status': 'active',
                    'source': 'NOAA NHC',
                    'link': link,
                }
                cyclones.append(cyclone_dict)

        except ET.ParseError as exc:
            logger.error('XML parse error for NHC feed: %s', exc)
        return cyclones

    def _parse_jtwc_data(self, xml_data):
        """
        Parse JTWC RSS data into cyclone dicts.

        Args:
            xml_data (str): Raw XML string.

        Returns:
            list[dict]: Cyclone dicts.
        """
        cyclones = []
        try:
            root = ET.fromstring(xml_data)
            channel = root.find('channel')
            if channel is None:
                return cyclones

            for item in channel.findall('item'):
                title = item.findtext('title', '')
                description = item.findtext('description', '')

                is_cyclone = any(
                    kw in title.lower()
                    for kw in ['typhoon', 'tropical storm', 'tropical depression', 'cyclone', 'warning']
                )
                if not is_cyclone:
                    continue

                lat, lon = self._extract_coords_from_description(description)

                cyclone_dict = {
                    'name': title.strip(),
                    'identifier': f'JTWC-{title.strip().replace(" ", "-")}',
                    'category': self._extract_category_from_title(title),
                    'intensity': None,
                    'lat': lat,
                    'lon': lon,
                    'movement_dir': None,
                    'movement_speed': None,
                    'central_pressure': None,
                    'max_wind_speed': None,
                    'basin': 'west_pacific',
                    'status': 'active',
                    'source': 'JTWC',
                }
                cyclones.append(cyclone_dict)

        except ET.ParseError as exc:
            logger.error('XML parse error for JTWC feed: %s', exc)
        return cyclones

    def _parse_imd_data(self, data):
        """
        Parse IMD cyclone bulletin data.

        Args:
            data (str): Raw XML/text from IMD feed.

        Returns:
            list[dict]: Cyclone dicts.
        """
        cyclones = []
        try:
            root = ET.fromstring(data)
            channel = root.find('channel')
            if channel is None:
                return cyclones

            for item in channel.findall('item'):
                title = item.findtext('title', '')
                description = item.findtext('description', '')

                is_cyclone = any(
                    kw in title.lower()
                    for kw in ['cyclone', 'cyclonic storm', 'depression', 'low pressure']
                )
                if not is_cyclone:
                    continue

                lat, lon = self._extract_coords_from_description(description)

                cyclone_dict = {
                    'name': title.strip(),
                    'identifier': f'IMD-{title.strip().replace(" ", "-")}',
                    'category': self._extract_category_from_title(title),
                    'intensity': None,
                    'lat': lat,
                    'lon': lon,
                    'movement_dir': None,
                    'movement_speed': None,
                    'central_pressure': None,
                    'max_wind_speed': None,
                    'basin': 'north_indian',
                    'status': 'active',
                    'source': 'IMD',
                }
                cyclones.append(cyclone_dict)

        except ET.ParseError as exc:
            logger.error('XML parse error for IMD feed: %s', exc)
        return cyclones

    # ------------------------------------------------------------------
    # Database persistence
    # ------------------------------------------------------------------

    def _save_cyclone(self, cyclone_data):
        """
        Save or update a cyclone record in the database.

        Args:
            cyclone_data (dict): Cyclone data dictionary.
        """
        try:
            identifier = cyclone_data.get('identifier')
            if not identifier:
                return

            existing = Cyclone.query.filter_by(identifier=identifier).first()
            if existing:
                # Update mutable fields
                existing.lat = cyclone_data.get('lat') or existing.lat
                existing.lon = cyclone_data.get('lon') or existing.lon
                existing.category = cyclone_data.get('category') or existing.category
                existing.max_wind_speed = cyclone_data.get('max_wind_speed') or existing.max_wind_speed
                existing.central_pressure = cyclone_data.get('central_pressure') or existing.central_pressure
                existing.movement_speed = cyclone_data.get('movement_speed') or existing.movement_speed
                existing.movement_dir = cyclone_data.get('movement_dir') or existing.movement_dir
                existing.status = cyclone_data.get('status', 'active')
                existing.last_updated = datetime.now(timezone.utc)
                db.session.commit()
            else:
                cyclone = Cyclone(
                    name=cyclone_data.get('name'),
                    identifier=identifier,
                    category=cyclone_data.get('category'),
                    intensity=cyclone_data.get('intensity'),
                    lat=cyclone_data.get('lat'),
                    lon=cyclone_data.get('lon'),
                    movement_dir=cyclone_data.get('movement_dir'),
                    movement_speed=cyclone_data.get('movement_speed'),
                    central_pressure=cyclone_data.get('central_pressure'),
                    max_wind_speed=cyclone_data.get('max_wind_speed'),
                    basin=cyclone_data.get('basin'),
                    status=cyclone_data.get('status', 'active'),
                    source=cyclone_data.get('source'),
                    first_detected=datetime.now(timezone.utc),
                )
                db.session.add(cyclone)
                db.session.commit()
                logger.info('Saved new cyclone: %s', cyclone_data.get('name'))
        except Exception as exc:
            db.session.rollback()
            logger.error('Failed to save cyclone %s: %s', cyclone_data.get('name'), exc)

    def _save_track_point(self, cyclone_id, point_data):
        """
        Save a cyclone track point to the database.

        Args:
            cyclone_id (int): Cyclone primary key.
            point_data (dict): Track point data.
        """
        try:
            tp = CycloneTrackPoint(
                cyclone_id=cyclone_id,
                lat=point_data['lat'],
                lon=point_data['lon'],
                timestamp=point_data.get('timestamp'),
                wind_speed=point_data.get('wind_speed'),
                pressure=point_data.get('pressure'),
                category=point_data.get('category'),
                is_forecast=point_data.get('is_forecast', False),
            )
            db.session.add(tp)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error('Failed to save track point for cyclone %s: %s', cyclone_id, exc)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_coords_from_description(description):
        """
        Attempt to extract latitude/longitude from a text description.

        Looks for patterns like "12.5N 85.3W" or "lat: 12.5, lon: -85.3".

        Args:
            description (str): Text to search.

        Returns:
            tuple: (lat, lon) floats or (None, None).
        """
        import re

        if not description:
            return None, None

        # Pattern: "12.5N 85.3W" or "12.5°N 85.3°W"
        pattern = r'(\d+\.?\d*)\s*°?\s*([NS])\s+(\d+\.?\d*)\s*°?\s*([EW])'
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            lat = float(match.group(1))
            if match.group(2).upper() == 'S':
                lat = -lat
            lon = float(match.group(3))
            if match.group(4).upper() == 'W':
                lon = -lon
            return lat, lon

        # Pattern: lat=12.5&lon=-85.3 or similar key-value
        lat_match = re.search(r'lat[=:]\s*(-?\d+\.?\d*)', description, re.IGNORECASE)
        lon_match = re.search(r'lon[=:]\s*(-?\d+\.?\d*)', description, re.IGNORECASE)
        if lat_match and lon_match:
            return float(lat_match.group(1)), float(lon_match.group(1))

        return None, None

    @staticmethod
    def _extract_category_from_title(title):
        """
        Extract cyclone category from a title string.

        Args:
            title (str): Advisory/bulletin title.

        Returns:
            str: Category label or 'Unknown'.
        """
        title_lower = title.lower()
        if 'category 5' in title_lower or 'super typhoon' in title_lower:
            return 'Category 5'
        if 'category 4' in title_lower:
            return 'Category 4'
        if 'category 3' in title_lower:
            return 'Category 3'
        if 'category 2' in title_lower:
            return 'Category 2'
        if 'category 1' in title_lower:
            return 'Category 1'
        if 'hurricane' in title_lower:
            return 'Hurricane'
        if 'typhoon' in title_lower:
            return 'Typhoon'
        if 'tropical storm' in title_lower:
            return 'Tropical Storm'
        if 'tropical depression' in title_lower or 'depression' in title_lower:
            return 'Tropical Depression'
        if 'cyclonic storm' in title_lower or 'cyclone' in title_lower:
            return 'Cyclonic Storm'
        return 'Unknown'
