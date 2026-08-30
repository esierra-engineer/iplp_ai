"""plpidap2.dat — simulation-independent aggregate aperture indices per stage. See scratchpad
spec: block_dependant_formats.md#plpidap2.dat. Bootstrapped data (see db/models.py's Phase 5
docstring)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ApertureIndexAggregate
from .common import DatWriter, fiscal_month


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(ApertureIndexAggregate).where(ApertureIndexAggregate.case_id == case_id)
    ).all()
    rows.sort(key=lambda r: r.stage.num_eta)

    w = DatWriter()
    w.comment("Archivo de caudales por etapa (plpidap2.dat)")
    w.comment("Numero de etapas con caudales")
    w.fields(len(rows))
    w.comment("Mes   Etapa  NApert ApertInd(1,...,NApert)")
    for r in rows:
        w.fields(
            f"{fiscal_month(r.stage.month):03d}",
            f"{r.stage.num_eta:03d}",
            len(r.apertures),
            *(f"{v:3d}" for v in r.apertures),
        )
    return w.render()
