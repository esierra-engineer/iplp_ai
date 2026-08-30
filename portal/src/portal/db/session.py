"""SQLAlchemy engine/session wiring.

One SQLite file backs every case; each domain table is scoped by ``case_id``
(see db/models.py) rather than one database per case, so cases can share
reference data or be cloned/diffed without juggling separate files.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# .../portal/src/portal/db/session.py -> up 4 levels -> .../portal/ (contains pyproject.toml)
DEFAULT_DB_PATH = os.environ.get("PORTAL_DB_PATH", os.path.join(_PROJECT_ROOT, "portal.sqlite3"))


def make_engine(db_path: str = DEFAULT_DB_PATH):
    return create_engine(f"sqlite:///{os.path.abspath(db_path)}", future=True)


_engine = make_engine()
SessionLocal = sessionmaker(bind=_engine, future=True, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session; commits on success, rolls back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session, always closes it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
