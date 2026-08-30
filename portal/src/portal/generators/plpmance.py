"""plpmance.dat — plant maintenance (Pmin/Pmax) by block. See scratchpad spec:
block_dependant_formats.md#plpmance.dat. Ranges from PlantMaintenance (MantCEN's pre-merged
block-range table) are expanded into one row per block here."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Block, Plant, PlantMaintenance, Stage
from .common import DatWriter, fiscal_month, number, quote


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(PlantMaintenance)
        .where(PlantMaintenance.case_id == case_id)
        .order_by(PlantMaintenance.plant_id, PlantMaintenance.block_start)
    ).all()
    by_plant: dict[Plant, list[PlantMaintenance]] = defaultdict(list)
    for r in rows:
        by_plant[r.plant].append(r)

    stage_by_id = {s.id: s for s in session.scalars(select(Stage).where(Stage.case_id == case_id))}
    month_by_num_blo = {
        b.num_blo: fiscal_month(stage_by_id[b.stage_id].month)
        for b in session.scalars(select(Block).where(Block.case_id == case_id))
    }

    w = DatWriter()
    w.comment("Archivo de mantenimientos de centrales (plpmance.dat)")
    w.comment("numero de centrales con matenimientos")
    w.fields(len(by_plant))
    for plant, ranges in by_plant.items():
        w.comment("Nombre de la central")
        w.fields(quote(plant.name))
        n_blo = sum(r.block_end - r.block_start + 1 for r in ranges)
        w.comment("Numero de Bloques e Intervalos")
        w.fields(n_blo, "01")
        w.comment("Mes    Bloque  NIntPot   PotMin   PotMax")
        for r in ranges:
            for num_blo in range(r.block_start, r.block_end + 1):
                w.fields(
                    f"{month_by_num_blo.get(num_blo, 0):02d}",
                    f"{num_blo:03d}",
                    1,
                    number(r.pot_min, 2),
                    number(r.pot_max, 2),
                )
    return w.render()
