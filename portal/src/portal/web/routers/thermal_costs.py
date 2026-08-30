"""Thermal cost schedule (plpcosce.dat source) list + edit. Paginated/searchable like Plants —
13,331 rows in this case (a stage-range per plant, not one row per stage)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...db.models import Case, Plant, ThermalCostSchedule
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/thermal-costs", tags=["thermal-costs"])

PAGE_SIZE = 50


@router.get("")
def list_schedules(
    request: Request,
    case_id: int,
    q: str | None = None,
    page: int = 1,
    session: Session = Depends(get_session),
):
    case = session.get(Case, case_id)
    stmt = (
        select(ThermalCostSchedule)
        .join(Plant, ThermalCostSchedule.plant_id == Plant.id)
        .where(ThermalCostSchedule.case_id == case_id)
    )
    if q:
        stmt = stmt.where(Plant.name.ilike(f"%{q}%"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    schedules = session.scalars(
        stmt.order_by(Plant.name, ThermalCostSchedule.stage_start)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return templates.TemplateResponse(
        request,
        "thermal_costs_list.html",
        {
            "case": case,
            "schedules": schedules,
            "q": q or "",
            "page": page,
            "total": total,
            "num_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        },
    )


@router.post("/{schedule_id}/update")
def update_schedule(
    case_id: int,
    schedule_id: int,
    cost_var: float = Form(...),
    session: Session = Depends(get_session),
):
    s = session.get(ThermalCostSchedule, schedule_id)
    s.cost_var = cost_var
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/thermal-costs?msg=Cost+updated", status_code=303)
