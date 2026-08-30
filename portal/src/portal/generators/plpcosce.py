"""plpcosce.dat — thermal plant variable cost by stage. See scratchpad spec:
block_dependant_formats.md#plpcosce.dat.

ThermalCostSchedule rows are (plant, stage_start, stage_end, cost) ranges from CV_MP's CENTRAL/
INICIAL/FINAL/[US$/MWh] columns (see db/models.py's docstring on how this was distinguished from
CV_MP's other, unrelated NAME/DATE1/DATE2/CV table) — expanded here into one row per stage, all
sharing that range's cost, rounded to 1 decimal (matches the golden file exactly, confirmed empirically).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Plant, Stage, ThermalCostSchedule
from .common import DatWriter, fiscal_month, number, quote


def generate(session: Session, case_id: int) -> str:
    schedules = session.scalars(
        select(ThermalCostSchedule)
        .where(ThermalCostSchedule.case_id == case_id)
        .order_by(ThermalCostSchedule.plant_id, ThermalCostSchedule.stage_start)
    ).all()
    by_plant: dict[Plant, list[ThermalCostSchedule]] = defaultdict(list)
    for s in schedules:
        by_plant[s.plant].append(s)

    stage_month = {
        s.num_eta: fiscal_month(s.month)
        for s in session.scalars(select(Stage).where(Stage.case_id == case_id))
    }

    w = DatWriter()
    w.comment("Archivo de precios de termicas (plpcosce.dat)")
    w.comment("Numero de centrales termicas con cambio de costo variable")
    w.fields(len(by_plant))
    for plant, ranges in by_plant.items():
        w.comment("Nombre de la central")
        w.fields(quote(plant.name))
        n_eta = sum(r.stage_end - r.stage_start + 1 for r in ranges)
        w.comment("Numero de etapas")
        w.fields(n_eta)
        w.comment("Mes   Etapa    CosVar")
        for r in ranges:
            for num_eta in range(r.stage_start, r.stage_end + 1):
                w.fields(f"{stage_month.get(num_eta, 0):02d}", f"{num_eta:03d}", number(r.cost_var, 1))
    return w.render()
