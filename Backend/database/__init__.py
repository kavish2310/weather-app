"""
Database initialization and session management for the Weather app.

Provides init_db(app) to bind SQLAlchemy to a Flask app and create all tables,
and get_db_session() for obtaining a scoped session.
"""

import os
import logging

from sqlalchemy import inspect, text

from Backend.models import db

logger = logging.getLogger(__name__)


def init_db(app):
    """
    Initialize the database with the given Flask application.

    Creates the data directory if it does not exist, binds SQLAlchemy to the
    app, and creates all tables defined in the models module.

    Args:
        app: The Flask application instance.
    """
    # Ensure the data directory exists for SQLite
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///') and ':memory:' not in db_uri:
        db_path = db_uri.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info('Created database directory: %s', db_dir)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        with db.engine.begin() as connection:
            for table in ('weather_observations', 'weather_forecasts'):
                columns = {column['name'] for column in inspect(connection).get_columns(table)}
                if 'source' not in columns:
                    connection.execute(text(
                        f'ALTER TABLE {table} ADD COLUMN source VARCHAR(64)'
                    ))
        logger.info('Database tables created successfully.')


def get_db_session():
    """
    Return the current SQLAlchemy database session.

    Must be called within a Flask application context.

    Returns:
        sqlalchemy.orm.scoping.scoped_session: The active database session.
    """
    return db.session
