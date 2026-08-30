"""plpfilemb.dat — reservoir filtrations. See scratchpad spec: static_formats.md#plpfilemb.dat.
No Excel source (see db/models.py's Phase 6 docstring) — bootstrapped."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ReservoirFiltration
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    reservoirs = session.scalars(
        select(ReservoirFiltration)
        .where(ReservoirFiltration.case_id == case_id)
        .order_by(ReservoirFiltration.id)
    ).all()
    w = DatWriter()
    w.comment("Archivo de Filtraciones de Embalses (plpfiln.dat)")
    w.comment("Numero Embalses con filtraciones")
    w.fields(len(reservoirs))
    for r in reservoirs:
        w.comment("Nombre de embalse")
        w.fields(quote(r.plant.name))
        w.comment("Filtraciones medias")
        w.fields(number(r.avg_filtration, 2))
        w.comment("Numero de Tramos")
        w.fields(len(r.segments))
        w.comment("Tramo    Vol[10e6 m3]  Pendiente   Constante")
        for i, seg in enumerate(r.segments, start=1):
            w.fields(i, number(seg["volume"], 1), number(seg["slope"], 9), number(seg["constant"], 9))
        w.comment("Nombre de la Central aguas abajo")
        w.fields(quote(r.downstream_plant.name))
    return w.render()
