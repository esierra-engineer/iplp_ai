"""plpvrebemb.dat — spill volumes. See scratchpad spec: static_formats.md#plpvrebemb.dat. No
Excel source (see db/models.py's Phase 6 docstring) — bootstrapped."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ReservoirSpillVolume
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    reservoirs = session.scalars(
        select(ReservoirSpillVolume)
        .where(ReservoirSpillVolume.case_id == case_id)
        .order_by(ReservoirSpillVolume.id)
    ).all()
    w = DatWriter()
    w.comment("Archivo de Volumenes de vertimiento de Embalses (plpvrebemb.dat)")
    w.comment("Numero Embalses con volumenes espe")
    w.fields(len(reservoirs))
    for r in reservoirs:
        w.comment("Nombre del Embalse")
        w.fields(quote(r.plant.name))
        w.comment("Volumen de Rebalse [ 10^3 m3 ]")
        w.fields(int(r.spill_volume))
        w.comment("Costo de Rebalse")
        # cost is a whole number for some reservoirs (e.g. 5000) but fractional for others (e.g.
        # 0.01) — golden values have at most 2 decimals, so use that rather than int() truncation.
        w.fields(number(r.cost, 2))
    return w.render()
