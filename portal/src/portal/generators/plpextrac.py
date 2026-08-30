"""plpextrac.dat — extractions. See scratchpad spec: static_formats.md#plpextrac.dat. No Excel
source (see db/models.py's Phase 6 docstring) — bootstrapped."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ExtractionPoint
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    points = session.scalars(
        select(ExtractionPoint).where(ExtractionPoint.case_id == case_id).order_by(ExtractionPoint.id)
    ).all()
    w = DatWriter()
    w.comment("Archivo de Extracciones (plpextrac.dat)")
    w.comment("Numero Centrales con extraccion")
    w.fields(len(points))
    for p in points:
        w.comment("Nombre de central de extraccion")
        w.fields(quote(p.source_plant.name))
        w.comment("Maxima Extraccion (m3/seg)")
        w.fields(number(p.max_extraction, 1))
        w.comment("Nombre de la Central aguas abajo")
        w.fields(quote(p.downstream_plant.name))
    return w.render()
