"""Database connection and lifecycle management for Expert Networks module."""

import os
from pathlib import Path
import databases

# Database path relative to backend directory
BACKEND_DIR = Path(__file__).parent.parent.parent
DATABASE_PATH = BACKEND_DIR / "expert_networks.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create database connection
database = databases.Database(DATABASE_URL)


async def get_database() -> databases.Database:
    """Get database connection."""
    return database


async def connect_db():
    """Connect to database on startup."""
    if not database.is_connected:
        await database.connect()


async def disconnect_db():
    """Disconnect from database on shutdown."""
    if database.is_connected:
        await database.disconnect()
