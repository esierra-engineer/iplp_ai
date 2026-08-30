"""Shared FastAPI dependencies/singletons used by every router (kept separate from app.py to avoid
a circular import between the app and its routers)."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from ..db.session import get_session  # noqa: F401  (re-exported for router convenience)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
