from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Battery, Case
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/batteries", tags=["batteries"])


@router.get("")
def list_batteries(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    batteries = session.scalars(
        select(Battery).where(Battery.case_id == case_id).order_by(Battery.bat_ind)
    ).all()
    return templates.TemplateResponse(
        request, "batteries_list.html", {"case": case, "batteries": batteries}
    )


@router.post("/{battery_id}/update")
def update_battery(
    case_id: int,
    battery_id: int,
    discharge_loss_factor: float = Form(...),
    capacity_min: float = Form(...),
    capacity_max: float = Form(...),
    session: Session = Depends(get_session),
):
    battery = session.get(Battery, battery_id)
    battery.discharge_loss_factor = discharge_loss_factor
    battery.capacity_min = capacity_min
    battery.capacity_max = capacity_max
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/batteries?msg=Battery+updated", status_code=303)
