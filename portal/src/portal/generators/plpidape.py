"""plpidape.dat — aperture indices per stage, per simulation. See scratchpad spec:
block_dependant_formats.md#plpidape.dat. Bootstrapped data (see db/models.py's Phase 5 docstring).
Etapa is restricted to 2..NEtapa in this file (stage 1 excluded) — ApertureIndexSimulation rows
simply don't exist for stage 1, so no special-casing is needed here."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import ApertureIndexSimulation
from .common import DatWriter, fiscal_month


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(ApertureIndexSimulation).where(ApertureIndexSimulation.case_id == case_id)
    ).all()
    by_sim: dict[int, list[ApertureIndexSimulation]] = defaultdict(list)
    for r in rows:
        by_sim[r.simulation_slot].append(r)
    n_simul = len(by_sim)
    n_eta_cau = len(by_sim[1]) if n_simul else 0

    w = DatWriter()
    w.comment("Archivo de caudales por etapa")
    w.comment("Numero de simulaciones y etapas con caudales")
    w.fields(n_simul, n_eta_cau)
    for sim_idx in sorted(by_sim):
        stage_rows = sorted(by_sim[sim_idx], key=lambda r: r.stage.num_eta)
        w.comment(f"Mes   Etapa  NApert ApertInd(1,...,NApert) - Simulacion={sim_idx:02d}")
        for r in stage_rows:
            w.fields(
                f"{fiscal_month(r.stage.month):03d}",
                f"{r.stage.num_eta:03d}",
                len(r.apertures),
                *(f"{v:3d}" for v in r.apertures),
            )
    return w.render()
