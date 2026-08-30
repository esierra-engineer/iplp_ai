from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.models import Bus, Case, IndustrialProject
from ..deps import get_session, templates

router = APIRouter(prefix="/cases/{case_id}/projects", tags=["projects"])


@router.get("")
def list_projects(request: Request, case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    projects = session.scalars(
        select(IndustrialProject)
        .where(IndustrialProject.case_id == case_id)
        .order_by(IndustrialProject.start_date)
    ).all()
    buses = session.scalars(select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)).all()
    return templates.TemplateResponse(
        request, "projects_list.html", {"case": case, "projects": projects, "buses": buses}
    )


@router.post("")
def create_project(
    case_id: int,
    bus_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    demand_mw: float = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_session),
):
    session.add(
        IndustrialProject(
            case_id=case_id,
            bus_id=bus_id,
            start_date=start_date,
            end_date=end_date,
            demand_mw=demand_mw,
            description=description or None,
        )
    )
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/projects?msg=Project+added", status_code=303)


@router.post("/{project_id}/update")
def update_project(
    case_id: int,
    project_id: int,
    bus_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    demand_mw: float = Form(...),
    description: str = Form(""),
    session: Session = Depends(get_session),
):
    p = session.get(IndustrialProject, project_id)
    p.bus_id = bus_id
    p.start_date = start_date
    p.end_date = end_date
    p.demand_mw = demand_mw
    p.description = description or None
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/projects?msg=Project+updated", status_code=303)


@router.post("/{project_id}/delete")
def delete_project(case_id: int, project_id: int, session: Session = Depends(get_session)):
    session.delete(session.get(IndustrialProject, project_id))
    session.commit()
    return RedirectResponse(f"/cases/{case_id}/projects?msg=Project+deleted", status_code=303)
