"""API dependencies for FastAPI endpoints."""

from app.db.session import get_db

# Re-export get_db for convenience
__all__ = ["get_db"]
