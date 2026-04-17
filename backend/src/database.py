"""Database configuration and session management.

This module configures the SQLite database connection using SQLModel
and provides session management for database operations.

Attributes:
    engine: SQLModel engine instance for database connections.
"""

from sqlmodel import create_engine
from sqlmodel import Session
from sqlmodel import SQLModel

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args=(
        {"check_same_thread": False}
        if "sqlite" in settings.database_url
        else {}
    ),
)


def create_db_and_tables() -> None:
    """Create all database tables defined in SQLModel metadata.

    This function should be called once during application startup
    to initialize the database schema. It creates tables for all
    SQLModel classes that have been imported and registered.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency function for FastAPI to inject database sessions.

    Yields:
        SQLModel Session instance for database operations.
        The session is automatically closed after the request completes.

    Example:
        >>> from fastapi import Depends
        >>> from .database import get_session
        >>>
        >>> @router.get("/items")
        >>> def get_items(session: Session = Depends(get_session)):
        >>>     return session.exec(select(Item)).all()
    """
    with Session(engine) as session:
        yield session
