"""plpmanli.dat — line maintenance by block. See scratchpad spec:
block_dependant_formats.md#plpmanli.dat. No Mes column here (unlike plpmance.dat)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Line, LineMaintenance
from .common import DatWriter, logical, number, quote


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(LineMaintenance)
        .where(LineMaintenance.case_id == case_id)
        .order_by(LineMaintenance.line_id, LineMaintenance.block_start)
    ).all()
    by_line: dict[Line, list[LineMaintenance]] = defaultdict(list)
    for r in rows:
        by_line[r.line].append(r)

    w = DatWriter()
    w.comment("Archivo de mantenimientos de lineas (plpmanli.dat)")
    w.comment("numero de lineas con matenimientos")
    w.fields(len(by_line))
    for line, ranges in by_line.items():
        w.comment("Nombre de la lineas")
        w.fields(quote(line.name))
        n_blo = sum(r.block_end - r.block_start + 1 for r in ranges)
        w.comment("Numero de Bloques con mantenimiento")
        w.fields(n_blo)
        w.comment("NumeroBloque PotMaxAB   PotMaxBA     Operativa")
        for r in ranges:
            for num_blo in range(r.block_start, r.block_end + 1):
                w.fields(f"{num_blo:03d}", number(r.capacity_ab, 1), number(r.capacity_ba, 1), logical(r.operational))
    return w.render()
