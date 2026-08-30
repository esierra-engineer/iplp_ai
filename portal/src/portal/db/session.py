"""SQLAlchemy engine/session wiring.

Historically one shared SQLite file backed every case (each domain table scoped by ``case_id``,
see db/models.py). As of the 2026-08-30 "every case is a sqlite file" change, the web app and CLI
instead give each case its own dedicated file under ``cases/`` (see db/registry.py) — `make_engine`/
`DEFAULT_DB_PATH`/`_engine`/`SessionLocal` below are kept as-is purely for the test suite (which
seeds one ad-hoc on-disk DB per test session directly via `make_engine`, bypassing the registry
entirely) and any other direct single-file use; `get_engine_for_path` is what the per-case-file web
layer actually uses.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# .../portal/src/portal/db/session.py -> up 4 levels -> .../portal/ (contains pyproject.toml)
DEFAULT_DB_PATH = os.environ.get("PORTAL_DB_PATH", os.path.join(_PROJECT_ROOT, "portal.sqlite3"))


def make_engine(db_path: str = DEFAULT_DB_PATH):
    return create_engine(f"sqlite:///{os.path.abspath(db_path)}", future=True)


_engine = make_engine()
SessionLocal = sessionmaker(bind=_engine, future=True, expire_on_commit=False)

# One SQLAlchemy engine (connection pool) per case file, reused across requests instead of
# reopening the SQLite file on every call — keyed by resolved absolute path.
_case_engine_cache: dict[str, "Engine"] = {}  # noqa: F821 (Engine imported lazily below only for typing)


def get_engine_for_path(path: str | Path):
    """Return the (cached) engine for a specific case file, creating it on first use."""
    key = str(Path(path).resolve())
    engine = _case_engine_cache.get(key)
    if engine is None:
        engine = make_engine(key)
        _case_engine_cache[key] = engine
    return engine


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
