"""Stage (calendar) list + edit. Create/delete are intentionally not exposed yet — adding or
removing a stage means renumbering every dependent Block, which Phase 1 doesn't attempt (see the
plan's Phase 1 scope: prove the CRUD pattern on the safe subset first)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Case, Stage
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/stages", tags=["stages"])


@router.get("")
def list_stages(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    stages = session.scalars(
        select(Stage).where(Stage.case_id == case_id).order_by(Stage.num_eta)
    ).all()
    return templates.TemplateResponse(request, "stages_list.html", {"case": case, "stages": stages})


@router.post("/{stage_id}/update")
def update_stage(
    case_id: int,
    stage_id: int,
    duration: int = Form(...),
    rate_factor: float = Form(...),
    hydro_dependent: bool = Form(False),
    label: str = Form(""),
    session: Session = Depends(get_session),
):
    stage = session.get(Stage, stage_id)
    stage.duration = duration
    stage.rate_factor = rate_factor
    stage.hydro_dependent = hydro_dependent
    stage.label = label
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/stages?msg=Stage+updated", status_code=303)
