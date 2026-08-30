from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...case_clone import clone_case_file
from ...db.models import Bus, Case, Line, Plant, Stage
from ...db.registry import list_case_files
from ..deps import get_session, templates

router = APIRouter(prefix="/cases", tags=["cases"])


def _count(session: Session, model, case_id: int) -> int:
    return session.scalar(select(func.count()).select_from(model).where(model.case_id == case_id))


@router.get("")
def list_cases(request: Request):
    # Each case is its own file now (see db/registry.py) — the list comes from the registry, not
    # any one case's own database. CaseFile already exposes the same id/name/description attributes
    # cases_list.html expects from a Case row, so the template is unchanged.
    cases = list_case_files()
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
):
    new_id = clone_case_file(case_id, new_name, description or None)
    return RedirectResponse(f"/cases/{new_id}?msg=Cloned+from+case+{case_id}", status_code=303)
