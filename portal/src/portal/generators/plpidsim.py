"""plpidsim.dat — simulation hydrology index by stage. See scratchpad spec:
block_dependant_formats.md#plpidsim.dat. Bootstrapped data (see db/models.py's Phase 5 docstring)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import HydrologyScenarioAssignment
from .common import DatWriter, fiscal_month


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(HydrologyScenarioAssignment)
        .where(HydrologyScenarioAssignment.case_id == case_id)
        .order_by(HydrologyScenarioAssignment.stage_id)
    ).all()
    rows.sort(key=lambda r: r.stage.num_eta)
    n_simul = len(rows[0].hydro_class_by_sim) if rows else 0

    w = DatWriter()
    w.comment("Archivo de caudales por etapa (plpidsim.dat)")
    w.comment("Numero de simulaciones y etapas con caudales")
    w.fields(n_simul, len(rows))
    w.comment("Mes   Etapa  SimulInd(1,...,NSimul)")
    for r in rows:
        w.fields(
            f"{fiscal_month(r.stage.month):03d}",
            f"{r.stage.num_eta:03d}",
            *(f"{v:3d}" for v in r.hydro_class_by_sim),
        )
    return w.render()
