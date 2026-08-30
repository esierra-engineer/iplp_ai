"""plpcenbat.dat — batteries. See scratchpad spec: static_formats.md#plpcenbat.dat.

Note the format quirk from the spec: battery and injector names are written WITHOUT quotes in the
golden sample (unlike almost every other name field), and Fortran list-directed READ accepts both
quoted and bare tokens — this generator matches the golden convention and emits them bare.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Battery
from .common import DatWriter, number


def generate(session: Session, case_id: int) -> str:
    batteries = session.scalars(
        select(Battery).where(Battery.case_id == case_id).order_by(Battery.bat_ind)
    ).all()
    max_iny = max((len(b.injectors) for b in batteries), default=0)

    w = DatWriter()
    w.comment("Archivo de caracteristicas de baterias (plpcenbat.dat)")
    w.comment("Numero de baterias total, Numero maximo de inyecciones")
    w.fields(len(batteries), max_iny)
    w.comment("Baterias")
    for b in batteries:
        w.fields(b.bat_ind, b.plant.name)
        w.comment("Numero de centrales que inyectan")
        w.fields(len(b.injectors))
        w.comment("Central que inyecta, Factor de perdida de carga")
        for inj in b.injectors:
            w.fields(inj.name, number(inj.loss_factor, 2))
        w.comment("Barra, Factor de perdida de carga, Capacidad minima, Capacidad maxima")
        w.fields(
            b.bus.num_bar,
            number(b.discharge_loss_factor, 2),
            number(b.capacity_min, 1),
            number(b.capacity_max, 1),
        )
    return w.render()
