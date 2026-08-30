"""plpbar.dat — bus/'Barra' config. See scratchpad spec: static_formats.md#plpbar.dat."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Bus
from .common import DatWriter, quote


def generate(session: Session, case_id: int) -> str:
    buses = session.scalars(
        select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)
    ).all()

    w = DatWriter()
    w.comment("Archivo con definicion de Barras (plpbar.dat)")
    w.comment("Numero de Barras")
    w.fields(len(buses))
    w.comment("Numero       Nombre")
    for bus in buses:
        w.fields(bus.num_bar, quote(bus.name))
    return w.render()
