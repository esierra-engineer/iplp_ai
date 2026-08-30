from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...case_clone import clone_case
from ...db.models import Bus, Case, Line, Plant, Stage
from ..deps import get_session, templates

router = APIRouter(prefix="/cases", tags=["cases"])


def _count(session: Session, model, case_id: int) -> int:
    return session.scalar(select(func.count()).select_from(model).where(model.case_id == case_id))


@router.get("")
def list_cases(request: Request, session: Session = Depends(get_session)):
    cases = session.scalars(select(Case).order_by(Case.id)).all()
    return templates.TemplateResponse(request, "cases_list.html", {"cases": cases})


@router.get("/{case_id}")
def case_overview(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    counts = {
        "buses": _count(session, Bus, case_id),
        "lines": _count(session, Line, case_id),
        "stages": _count(session, Stage, case_id),
        "plants": _count(session, Plant, case_id),
    }
    return templates.TemplateResponse(
        request, "case_overview.html", {"case": case, "counts": counts}
    )


@router.post("/{case_id}/clone")
def clone(
    case_id: int,
    new_name: str = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_session),
):
    new_case = clone_case(session, case_id, new_name, description or None)
    session.commit()
    return RedirectResponse(f"/cases/{new_case.id}?msg=Cloned+from+case+{case_id}", status_code=303)
