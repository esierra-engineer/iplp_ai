"""Shared FastAPI dependencies/singletons used by every router (kept separate from app.py to avoid
a circular import between the app and its routers).

`get_session` used to bind straight to one shared engine; every case now lives in its own SQLite
file (see db/registry.py), so it instead resolves the `case_id` path parameter — already present on
every case-scoped route via that router's `/cases/{case_id}/...` prefix — to that case's own file
and opens a session there. FastAPI matches this by parameter *name* against the route's path
template, so every existing router/endpoint that already declares `case_id: int` and
`Depends(get_session)` keeps working completely unchanged.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, sessionmaker

from ..db.registry import resolve_case_path
from ..db.session import get_engine_for_path

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_session(case_id: int) -> Iterator[Session]:
    path = resolve_case_path(case_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail=f"No case with id {case_id}")
    engine = get_engine_for_path(path)
    session = sessionmaker(bind=engine, future=True, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
