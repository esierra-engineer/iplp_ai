from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from portal.db.migrate_from_xlsm import import_case
from portal.db.models import Base
from portal.db.session import make_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


@pytest.fixture(scope="session")
def _seeded_engine(tmp_path_factory):
    """Build one on-disk SQLite DB, seeded once from the live .xlsm + current golden .dat files,
    shared read-only by every test in the session (Phase 1 has only one case so far)."""
    db_path = tmp_path_factory.mktemp("db") / "portal_test.sqlite3"
    engine = make_engine(str(db_path))
    Base.metadata.create_all(engine)
    with Session(engine, future=True) as session:
        case = import_case(
            session,
            case_name="phase1-test",
            xlsm_path=REPO_ROOT / "xlsm" / "IPLP20251001_c00.xlsm",
            dat_static_dir=REPO_ROOT / "dat" / "static",
            dat_block_dependant_dir=REPO_ROOT / "dat" / "block_dependant",
        )
        session.commit()
        cid = case.id
    return engine, cid


@pytest.fixture(scope="session")
def case_id(_seeded_engine) -> int:
    return _seeded_engine[1]


@pytest.fixture()
def session(_seeded_engine) -> Session:
    engine, _ = _seeded_engine
    with Session(engine, future=True) as s:
        yield s


def golden(*parts: str) -> str:
    # latin-1 decodes every byte 0-255 without error (a safe superset read for the plain-ASCII
    # files too) — some golden files (e.g. plpcenre.dat) have Latin-1 accented bytes in comment
    # lines, which the Fortran reader never inspects but Python's strict ascii codec would reject.
    return (GOLDEN_DIR.joinpath(*parts)).read_text(encoding="latin-1")
