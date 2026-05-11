"""Test fixtures — only load database fixtures when sqlmodel is available."""

import pytest

try:
    from sqlmodel import SQLModel, Session, create_engine
    from sqlmodel.pool import StaticPool
    _has_sqlmodel = True
except ImportError:
    _has_sqlmodel = False


@pytest.fixture(name="session")
def session_fixture():
    if not _has_sqlmodel:
        pytest.skip("sqlmodel not installed")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
