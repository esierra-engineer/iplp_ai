"""Runs every generator implemented so far for a case and lets the user preview or download the
result — the web replacement for running the `Archivo_NN` VBA macros by hand in Excel."""

from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from ...db.models import Case
from ...generators import (
    plpbar,
    plpblo,
    plpcenbat,
    plpcenpmax,
    plpcenre,
    plpcnfce,
    plpcnfli,
    plpdeb,
    plpeta,
    plpmat,
    plprun,
)
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/generate", tags=["generate"])

# Filename -> generator module. Extend this as later phases add generators.
GENERATORS = {
    "plpbar.dat": plpbar,
    "plpeta.dat": plpeta,
    "plpblo.dat": plpblo,
    "plpcnfli.dat": plpcnfli,
    "plpmat.dat": plpmat,
    "plpdeb.dat": plpdeb,
    "plprun.dat": plprun,
    "plpcnfce.dat": plpcnfce,
    "plpcenre.dat": plpcenre,
    "plpcenpmax.dat": plpcenpmax,
    "plpcenbat.dat": plpcenbat,
}


def _generate_all(session: Session, case_id: int) -> dict[str, str]:
    return {filename: mod.generate(session, case_id) for filename, mod in GENERATORS.items()}


@router.get("")
def generate_index(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    return templates.TemplateResponse(
        request, "generate.html", {"case": case, "filenames": list(GENERATORS)}
    )


@router.get("/preview/{filename}")
def preview_file(case_id: int, filename: str, session: Session = Depends(get_session)):
    if filename not in GENERATORS:
        return PlainTextResponse(f"Unknown file: {filename}", status_code=404)
    text = GENERATORS[filename].generate(session, case_id)
    return PlainTextResponse(text)


@router.get("/download.zip")
def download_zip(case_id: int, session: Session = Depends(get_session)):
    files = _generate_all(session, case_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, text in files.items():
            zf.writestr(filename, text)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=plp_case_dat_files.zip"},
    )
