"""Web UI for Phase 6's basin conventions: Ralco/Extraction/Filtration/SpillVolume (small,
normalized tables) plus the Maule/Laja convention line editors (see BasinConventionLine's
docstring for why those two are a verbatim line sequence rather than per-field forms)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import (
    BasinConventionLine,
    Case,
    ExtractionPoint,
    RalcoConvention,
    ReservoirFiltration,
    ReservoirSpillVolume,
)
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/basin-conventions", tags=["basin-conventions"])


@router.get("")
def overview(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    ralco = session.get(RalcoConvention, case_id)
    extraction_points = session.scalars(
        select(ExtractionPoint).where(ExtractionPoint.case_id == case_id)
    ).all()
    filtrations = session.scalars(
        select(ReservoirFiltration).where(ReservoirFiltration.case_id == case_id)
    ).all()
    spill_volumes = session.scalars(
        select(ReservoirSpillVolume).where(ReservoirSpillVolume.case_id == case_id)
    ).all()
    return templates.TemplateResponse(
        request,
        "basin_conventions.html",
        {
            "case": case,
            "ralco": ralco,
            "extraction_points": extraction_points,
            "filtrations": filtrations,
            "spill_volumes": spill_volumes,
        },
    )


@router.post("/spill-volume/{row_id}/update")
def update_spill_volume(
    case_id: int, row_id: int, spill_volume: float = Form(...), cost: float = Form(...),
    session: Session = Depends(get_session),
):
    row = session.get(ReservoirSpillVolume, row_id)
    row.spill_volume = spill_volume
    row.cost = cost
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/basin-conventions?msg=Updated", status_code=303)


@router.post("/filtration/{row_id}/update")
def update_filtration(
    case_id: int, row_id: int, avg_filtration: float = Form(...), session: Session = Depends(get_session)
):
    row = session.get(ReservoirFiltration, row_id)
    row.avg_filtration = avg_filtration
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/basin-conventions?msg=Updated", status_code=303)


@router.post("/extraction/{row_id}/update")
def update_extraction(
    case_id: int, row_id: int, max_extraction: float = Form(...), session: Session = Depends(get_session)
):
    row = session.get(ExtractionPoint, row_id)
    row.max_extraction = max_extraction
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/basin-conventions?msg=Updated", status_code=303)


@router.get("/{convention}/lines")
def convention_lines(
    request: Request, case_id: int, convention: str, session: Session = Depends(get_session)
):
    case = session.get(Case, case_id)
    lines = session.scalars(
        select(BasinConventionLine)
        .where(BasinConventionLine.case_id == case_id, BasinConventionLine.convention == convention.upper())
        .order_by(BasinConventionLine.line_order)
    ).all()
    return templates.TemplateResponse(
        request,
        "basin_convention_lines.html",
        {"case": case, "convention": convention.upper(), "lines": lines},
    )


@router.post("/line/{line_id}/update")
def update_line(
    case_id: int, line_id: int, text: str = Form(...), session: Session = Depends(get_session)
):
    row = session.get(BasinConventionLine, line_id)
    row.text = text
    session.commit()
    return RedirectResponse(
        f"/cases/{case_id}/basin-conventions/{row.convention}/lines?msg=Updated", status_code=303
    )
