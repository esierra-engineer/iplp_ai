"""Runs every generator implemented so far for a case and lets the user preview or download the
result — the web replacement for running the `Archivo_NN` VBA macros by hand in Excel."""

from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from ... import demand_calc
from ...db.models import Case
from ...generators import (
    indhor,
    plpaflce,
    plpbar,
    plpblo,
    plpcenbat,
    plpcenpmax,
    plpcenre,
    plpcnfce,
    plpcnfli,
    plpcosce,
    plpdeb,
    plpdem,
    plpeta,
    plpextrac,
    plpfilemb,
    plpidap2,
    plpidape,
    plpidsim,
    plplajam,
    plpmanbat,
    plpmance,
    plpmanem,
    plpmanli,
    plpmat,
    plpmaulen,
    plpminembh,
    plpralco,
    plprun,
    plpvrebemb,
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
    "plpdem.dat": plpdem,
    "indhor.csv": indhor,
    "plpcosce.dat": plpcosce,
    "plpmance.dat": plpmance,
    "plpmanli.dat": plpmanli,
    "plpmanem.dat": plpmanem,
    "plpminembh.dat": plpminembh,
    "plpmanbat.dat": plpmanbat,
    "plpaflce.dat": plpaflce,
    "plpidsim.dat": plpidsim,
    "plpidape.dat": plpidape,
    "plpidap2.dat": plpidap2,
    "plpralco.dat": plpralco,
    "plpextrac.dat": plpextrac,
    "plpfilemb.dat": plpfilemb,
    "plpvrebemb.dat": plpvrebemb,
    "plpmaulen.dat": plpmaulen,
    "plplajam.dat": plplajam,
}


def _generate_all(session: Session, case_id: int) -> dict[str, str]:
    # plpdem.dat and indhor.csv both need demand_calc.compute(), which is the slow part of this
    # whole pipeline (~10s for this case) — compute it once and hand it to both rather than
    # letting each generator redo it independently.
    shared_demand = demand_calc.compute(session, case_id)
    files = {}
    for filename, mod in GENERATORS.items():
        if mod in (plpdem, indhor):
            files[filename] = mod.generate(session, case_id, shared_demand)
        else:
            files[filename] = mod.generate(session, case_id)
    return files


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
