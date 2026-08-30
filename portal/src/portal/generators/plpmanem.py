"""plpmanem.dat — reservoir maintenance (VolMin/VolMax) by stage. See scratchpad spec:
block_dependant_formats.md#plpmanem.dat."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Plant, ReservoirMaintenance, Stage
from .common import DatWriter, fiscal_month, number, quote


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(ReservoirMaintenance)
        .where(ReservoirMaintenance.case_id == case_id)
        .order_by(ReservoirMaintenance.plant_id, ReservoirMaintenance.stage_start)
    ).all()
    by_plant: dict[Plant, list[ReservoirMaintenance]] = defaultdict(list)
    for r in rows:
        by_plant[r.plant].append(r)

    stage_month = {
        s.num_eta: fiscal_month(s.month)
        for s in session.scalars(select(Stage).where(Stage.case_id == case_id))
    }

    w = DatWriter()
    w.comment("Archivo de mantenimientos embalses (plpmanem.dat)")
    w.comment("Numero de embalses con mantenimientos")
    w.fields(len(by_plant))
    for plant, ranges in by_plant.items():
        w.comment("Nombre del embalse")
        w.fields(quote(plant.name))
        n_eta = sum(r.stage_end - r.stage_start + 1 for r in ranges)
        w.comment("Numero de Etapas con mantenimiento")
        w.fields(n_eta)
        w.comment("Mes   Etapa     VolMin     VolMax")
        for r in ranges:
            for num_eta in range(r.stage_start, r.stage_end + 1):
                w.fields(
                    f"{stage_month.get(num_eta, 0):02d}",
                    f"{num_eta:03d}",
                    number(r.vol_min, 7),
                    number(r.vol_max, 7),
                )
    return w.render()
