from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Bus, Case
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/buses", tags=["buses"])


@router.get("")
def list_buses(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    buses = session.scalars(select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)).all()
    return templates.TemplateResponse(request, "buses_list.html", {"case": case, "buses": buses})


@router.post("")
def create_bus(
    case_id: int,
    num_bar: int = Form(...),
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    session.add(Bus(case_id=case_id, num_bar=num_bar, name=name))
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/buses?msg=Bus+added", status_code=303)


@router.post("/{bus_id}/update")
def update_bus(
    case_id: int,
    bus_id: int,
    num_bar: int = Form(...),
    name: str = Form(...),
    session: Session = Depends(get_session),
):
    bus = session.get(Bus, bus_id)
    bus.num_bar = num_bar
    bus.name = name
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/buses?msg=Bus+updated", status_code=303)


@router.post("/{bus_id}/delete")
def delete_bus(case_id: int, bus_id: int, session: Session = Depends(get_session)):
    bus = session.get(Bus, bus_id)
    session.delete(bus)
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/buses?msg=Bus+deleted", status_code=303)
