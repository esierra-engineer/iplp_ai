"""plpcenre.dat — reservoir yield ('Rendimiento') curves. See scratchpad spec:
static_formats.md#plpcenre.dat. No confirmed Excel/VBA source (see db/models.py's
ReservoirYieldCurve docstring) — this file's data is only ever bootstrapped from a golden file."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ReservoirYieldCurve
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    curves = session.scalars(
        select(ReservoirYieldCurve).where(ReservoirYieldCurve.case_id == case_id).order_by(
            ReservoirYieldCurve.id
        )
    ).all()

    w = DatWriter()
    w.comment("Archivo de Rendimiento de Embalses (plpcenre.dat)")
    w.comment("Numero de Embalses con Rendimiento")
    w.fields(len(curves))
    for c in curves:
        w.comment("Nombre de Central")
        w.fields(quote(c.plant.name))
        w.comment("Nombre del Embalse")
        w.fields(quote(c.reservoir_plant.name))
        w.comment("Rendimiento Medio")
        w.fields(number(c.avg_yield, 3))
        w.comment("Numero de Tramos")
        w.fields(len(c.segments))
        w.comment("Tramo      Volumen     Pendiente    Constante  F.Escala")
        for seg in c.segments:
            w.fields(seg.ind, number(seg.volume, 7), number(seg.slope, 7), number(seg.constant, 7), seg.scale)
    return w.render()
