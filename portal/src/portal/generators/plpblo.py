"""plpblo.dat — block ('Bloque') durations within stages. See scratchpad spec:
block_dependant_formats.md#plpblo.dat. Row order is significant: the Fortran reader requires
NumBlo to equal the row's position, so blocks must be emitted in num_blo order (enforced by the
ORDER BY below, not by any DB-level ordering constraint)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Block
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    blocks = session.scalars(
        select(Block).where(Block.case_id == case_id).order_by(Block.num_blo)
    ).all()

    w = DatWriter()
    w.comment("Archivo con la duracion de los bloques")
    w.comment("Bloques")
    w.fields(len(blocks))
    w.comment("Bloque   Etapa   NHoras  Ano   Mes  TipoBloque")
    for b in blocks:
        stage = b.stage
        w.fields(
            f"{b.num_blo:03d}",
            f"{stage.num_eta:03d}",
            f"{int(b.duration):03d}",
            f"{b.year:03d}",
            f"{b.month:03d}",
            quote(b.label or f"Bloque {b.num_blo:02d}"),
        )
    return w.render()
