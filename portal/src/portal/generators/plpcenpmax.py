"""plpcenpmax.dat — Pmax-vs-volume curves. See scratchpad spec: static_formats.md#plpcenpmax.dat.
Same no-Excel-source situation as plpcenre.dat — see db/models.py's ReservoirPmaxCurve docstring."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ReservoirPmaxCurve
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    curves = session.scalars(
        select(ReservoirPmaxCurve).where(ReservoirPmaxCurve.case_id == case_id).order_by(
            ReservoirPmaxCurve.id
        )
    ).all()

    w = DatWriter()
    w.comment("Archivo con cuva pmax en funcion del volumen")
    w.comment("Numero de embalses")
    w.fields(len(curves))
    for c in curves:
        w.comment("Nombre de Central")
        w.fields(quote(c.plant.name))
        w.comment("Nombre Embalse")
        w.fields(quote(c.reservoir_plant.name))
        w.comment("Numero de Segmentos")
        w.fields(len(c.segments))
        w.comment("Volumen [10e6 m3]			Pendiente		Coeficiente")
        for seg in c.segments:
            w.fields(number(seg.volume, 4), number(seg.slope, 9), number(seg.constant, 8))
    return w.render()
