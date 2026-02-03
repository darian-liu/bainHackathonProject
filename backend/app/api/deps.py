"""Dependency injection for API routes."""
from app.core.config import settings


def get_settings():
    """Get application settings."""
    return settings
