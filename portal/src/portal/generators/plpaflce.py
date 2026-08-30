"""plpaflce.dat — inflows by plant by block/hydrology-class. See scratchpad spec:
block_dependant_formats.md#plpaflce.dat. Bootstrapped data (see db/models.py's Phase 5 docstring)
— this generator just reads Inflow back out in the file's exact shape, no algorithm involved."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Block, Inflow, Plant, Stage
from .common import DatWriter, fiscal_month, number, quote


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(Inflow).where(Inflow.case_id == case_id).order_by(Inflow.plant_id, Inflow.num_blo)
    ).all()
    by_plant: dict[Plant, list[Inflow]] = defaultdict(list)
    n_clase = 0
    for r in rows:
        by_plant[r.plant].append(r)
        n_clase = max(n_clase, len(r.values))

    stage_by_id = {s.id: s for s in session.scalars(select(Stage).where(Stage.case_id == case_id))}
    month_by_num_blo = {
        b.num_blo: fiscal_month(stage_by_id[b.stage_id].month)
        for b in session.scalars(select(Block).where(Block.case_id == case_id))
    }

    w = DatWriter()
    w.comment("Archivo de caudales por etapa")
    w.comment("Nro. Cent. c/Caudales Estoc. (EstocNVar2) y Nro. Hidrologias (NClase)")
    w.fields(len(by_plant), n_clase)
    for plant, blocks in by_plant.items():
        w.comment("Nombre de la central")
        w.fields(quote(plant.name))
        w.comment("Numero de bloques con caudales")
        w.fields(len(blocks))
        w.comment("Mes   Bloque    Caudal")
        for b in blocks:
            w.fields(
                f"{month_by_num_blo.get(b.num_blo, 0):03d}",
                f"{b.num_blo:03d}",
                *(number(v, 2) for v in b.values),
            )
    return w.render()
