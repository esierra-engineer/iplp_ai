from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Bus, Case, Line
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/lines", tags=["lines"])


@router.get("")
def list_lines(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    lines = session.scalars(select(Line).where(Line.case_id == case_id).order_by(Line.id)).all()
    buses = session.scalars(select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)).all()
    return templates.TemplateResponse(
        request, "lines_list.html", {"case": case, "lines": lines, "buses": buses}
    )


@router.post("")
def create_line(
    case_id: int,
    name: str = Form(...),
    bus_from_id: int = Form(...),
    bus_to_id: int = Form(...),
    capacity_ab: float = Form(...),
    capacity_ba: float = Form(...),
    voltage_kv: float = Form(...),
    resistance: float = Form(...),
    reactance: float = Form(...),
    models_losses: bool = Form(False),
    num_segments: int = Form(1),
    operational: bool = Form(True),
    session: Session = Depends(get_session),
):
    session.add(
        Line(
            case_id=case_id,
            name=name,
            bus_from_id=bus_from_id,
            bus_to_id=bus_to_id,
            capacity_ab=capacity_ab,
            capacity_ba=capacity_ba,
            voltage_kv=voltage_kv,
            resistance=resistance,
            reactance=reactance,
            models_losses=models_losses,
            num_segments=num_segments,
            operational=operational,
        )
    )
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/lines?msg=Line+added", status_code=303)


@router.post("/{line_id}/update")
def update_line(
    case_id: int,
    line_id: int,
    name: str = Form(...),
    bus_from_id: int = Form(...),
    bus_to_id: int = Form(...),
    capacity_ab: float = Form(...),
    capacity_ba: float = Form(...),
    voltage_kv: float = Form(...),
    resistance: float = Form(...),
    reactance: float = Form(...),
    models_losses: bool = Form(False),
    num_segments: int = Form(1),
    operational: bool = Form(True),
    session: Session = Depends(get_session),
):
    line = session.get(Line, line_id)
    line.name = name
    line.bus_from_id = bus_from_id
    line.bus_to_id = bus_to_id
    line.capacity_ab = capacity_ab
    line.capacity_ba = capacity_ba
    line.voltage_kv = voltage_kv
    line.resistance = resistance
    line.reactance = reactance
    line.models_losses = models_losses
    line.num_segments = num_segments
    line.operational = operational
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/lines?msg=Line+updated", status_code=303)


@router.post("/{line_id}/delete")
def delete_line(case_id: int, line_id: int, session: Session = Depends(get_session)):
    line = session.get(Line, line_id)
    session.delete(line)
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/lines?msg=Line+deleted", status_code=303)
