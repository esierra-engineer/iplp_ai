"""portal — SQLite + Python + web replacement for the PLP Excel/VBA case-data authoring pipeline.

CLI entry point (`uv run portal import-xlsm ...`) seeds the real app database (see db/session.py's
PORTAL_DB_PATH) from a case's .xlsm and current golden .dat files, for use with the web app
(`uv run uvicorn portal.web.app:app --reload`).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="portal")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import-xlsm", help="Seed the database with a new case from an .xlsm")
    imp.add_argument("--name", required=True, help="Case name (must be unique)")
    imp.add_argument("--xlsm", required=True, type=Path, help="Path to the case's .xlsm")
    imp.add_argument(
        "--dat-static",
        required=False,
        default=None,
        type=Path,
        help="Path to that case's dat/static/ (optional — omit to import from the .xlsm alone; "
        "the handful of fields with no Excel source are then left at sensible defaults/empty, "
        "see migrate_from_xlsm.py's module docstring)",
    )
    imp.add_argument(
        "--dat-block-dependant",
        required=False,
        default=None,
        type=Path,
        help="Path to dat/block_dependant/ (optional — same xlsm-alone fallback as --dat-static)",
    )
    imp.add_argument("--description", default=None)

    args = parser.parse_args()

    if args.command == "import-xlsm":
        from .db.migrate_from_xlsm import import_case
        from .db.models import Base
        from .db.session import SessionLocal, _engine

        Base.metadata.create_all(_engine)
        with SessionLocal() as session:
            case = import_case(
                session,
                case_name=args.name,
                xlsm_path=args.xlsm,
                dat_static_dir=args.dat_static,
                dat_block_dependant_dir=args.dat_block_dependant,
                description=args.description,
            )
            session.commit()
            print(f"Imported case {case.name!r} (id={case.id})")
