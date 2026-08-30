"""plpralco.dat — Ralco discharge-restriction curve. See scratchpad spec:
static_formats.md#plpralco.dat. No Excel source (see db/models.py's Phase 6 docstring) — bootstrapped."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.models import RalcoConvention
from .common import DatWriter, quote


def generate(session: Session, case_id: int) -> str:
    conv = session.get(RalcoConvention, case_id)
    w = DatWriter()
    w.comment("Archivo con la definicion de resrticcion de Ralco")
    w.comment("Nombre Lago Ralco. Restriccion desemba")
    w.fields(quote(conv.plant.name))
    w.comment("Numero de Segmentos Qdes")
    w.fields(len(conv.segments))
    w.comment("Vcota [10^3 m3/s]  a  b")
    for seg in conv.segments:
        w.fields(seg["volume"], seg["b"], seg["a"])
    return w.render()
