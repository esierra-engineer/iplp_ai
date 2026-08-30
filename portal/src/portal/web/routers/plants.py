"""Plant fleet list + edit. With ~2964 rows in this case, the list is paginated and filterable by
type/name; create/delete aren't exposed yet (a new plant needs a cen_ind assigned and, for
Embalse-type plants, a Reservoir row — same "safe subset first" reasoning as stages in Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...db.models import PLANT_TYPES, Bus, Case, Plant
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/plants", tags=["plants"])

PAGE_SIZE = 50


@router.get("")
def list_plants(
    request: Request,
    case_id: int,
    plant_type: str | None = None,
    q: str | None = None,
    page: int = 1,
    session: Session = Depends(get_session),
):
    case = session.get(Case, case_id)
    stmt = select(Plant).where(Plant.case_id == case_id)
    if plant_type:
        stmt = stmt.where(Plant.plant_type == plant_type)
    if q:
        stmt = stmt.where(Plant.name.ilike(f"%{q}%"))
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    plants = session.scalars(
        stmt.order_by(Plant.plant_type, Plant.cen_ind).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()
    buses = session.scalars(select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)).all()
    return templates.TemplateResponse(
        request,
        "plants_list.html",
        {
            "case": case,
            "plants": plants,
            "buses": buses,
            "plant_types": PLANT_TYPES,
            "plant_type": plant_type or "",
            "q": q or "",
            "page": page,
            "total": total,
            "num_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        },
    )


@router.post("/{plant_id}/update")
def update_plant(
    case_id: int,
    plant_id: int,
    bus_id: int = Form(...),
    cos_var: float = Form(...),
    rendimiento: float = Form(...),
    pot_min: float = Form(...),
    pot_max: float = Form(...),
    session: Session = Depends(get_session),
):
    plant = session.get(Plant, plant_id)
    plant.bus_id = bus_id or None
    plant.cos_var = cos_var
    plant.rendimiento = rendimiento
    plant.pot_min = pot_min
    plant.pot_max = pot_max
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/plants?msg=Plant+updated", status_code=303)
