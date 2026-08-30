"""Case registry: a small separate SQLite database (`cases/_registry.sqlite3`) that indexes where
each case's *own* dedicated SQLite file lives.

Per the user's 2026-08-30 request ("I want every case to be a sqlite file"), each case's data is
now a physically separate `.sqlite3` file under `cases/` (schema per db/models.py, exactly as
before) rather than one row among many in a single shared database. Every table in that schema is
still scoped by a `case_id` column/PK, and every existing query, generator, and web route still
filters on it unchanged — the one new invariant this module exists to guarantee is that **a case
file's own internal `Case.id` always equals the case_id this registry assigned it**, so a case_id
appearing in a URL or a generator call resolves to both "which file" (via this registry) and "which
row in that file" (still just `Case.id`, unchanged) without needing to touch that call site.

This registry is deliberately tiny and separate from db/models.py's `Base` — it never holds case
data itself (name/description are duplicated here only so the case list page and clone don't need
to open every file just to show a name), and losing/rebuilding it doesn't lose any case data, only
the id->file mapping (which can be reconstructed by scanning `cases/*.sqlite3` and reading each
file's own Case row, if that's ever needed).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, create_engine, func, select
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column, sessionmaker

_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../db/registry.py -> up 3 -> portal/
CASES_DIR = Path(os.environ.get("PORTAL_CASES_DIR", _PROJECT_ROOT / "cases"))
REGISTRY_DB_PATH = CASES_DIR / "_registry.sqlite3"

RegistryBase = declarative_base()


class CaseFile(RegistryBase):
    """One row per case: `id` is the same value stored as `Case.id` inside that case's own file."""

    __tablename__ = "case_file"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    file_name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[object] = mapped_column(DateTime, server_default=func.now())

    @property
    def path(self) -> Path:
        return CASES_DIR / self.file_name


_registry_engine = None
_RegistrySession = None


def _engine():
    global _registry_engine, _RegistrySession
    if _registry_engine is None:
        CASES_DIR.mkdir(parents=True, exist_ok=True)
        _registry_engine = create_engine(f"sqlite:///{REGISTRY_DB_PATH}", future=True)
        RegistryBase.metadata.create_all(_registry_engine)
        _RegistrySession = sessionmaker(bind=_registry_engine, future=True)
    return _registry_engine


def _session() -> Session:
    _engine()
    return _RegistrySession()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return slug or "case"


def register_case(name: str, description: str | None = None) -> tuple[int, Path]:
    """Allocate a new case_id + a not-yet-created file path for it. The caller is responsible for
    actually creating the SQLite file at the returned path and giving its Case row this same id
    (see db/migrate_from_xlsm.import_case's `case_id` parameter)."""
    with _session() as s:
        if s.scalar(select(CaseFile).where(CaseFile.name == name)) is not None:
            raise ValueError(f"a case named {name!r} already exists")
        base_slug = _slugify(name)
        file_name = f"{base_slug}.sqlite3"
        n = 1
        existing = {cf.file_name for cf in s.scalars(select(CaseFile))}
        while file_name in existing:
            n += 1
            file_name = f"{base_slug}_{n}.sqlite3"
        case_file = CaseFile(name=name, file_name=file_name, description=description)
        s.add(case_file)
        s.commit()
        return case_file.id, CASES_DIR / file_name


def resolve_case_path(case_id: int) -> Path | None:
    with _session() as s:
        cf = s.get(CaseFile, case_id)
        return cf.path if cf is not None else None


def get_case_file(case_id: int) -> CaseFile | None:
    with _session() as s:
        cf = s.get(CaseFile, case_id)
        if cf is not None:
            s.expunge(cf)
        return cf


def list_case_files() -> list[CaseFile]:
    with _session() as s:
        rows = s.scalars(select(CaseFile).order_by(CaseFile.id)).all()
        for r in rows:
            s.expunge(r)
        return rows


def rename_case_file(case_id: int, new_name: str, new_description: str | None) -> None:
    with _session() as s:
        cf = s.get(CaseFile, case_id)
        if cf is not None:
            cf.name = new_name
            cf.description = new_description
            s.commit()
