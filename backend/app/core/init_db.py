"""Database initialization script."""

import logging
from app.core.database import Base, engine
from app.models.judgement import Judgement

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initialize the database by creating all tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.") 