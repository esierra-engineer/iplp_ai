"""plpdem.dat — demand by bus by block. See scratchpad spec: block_dependant_formats.md#plpdem.dat.

Values come from demand_calc.compute() (a port of Rutina04.DEMxBarra2 + the block-aggregation loop
in Archivo_03_PLPDEM_5A — see that module's docstring for the algorithm). This generator always
writes the MULTINODAL shape (matches this case: Barras has 241 system buses, only ~139 of which
have demand-profile data and get real rows; the rest get `NumDemandas=0`, and the header count is
the *system* bus total, not the demand-bearing subset — per the VBA writer's own MULTINODAL branch).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import demand_calc
from ..db.models import Block, Bus, Stage
from .common import DatWriter, fiscal_month, number, quote


def generate(
    session: Session, case_id: int, _result: demand_calc.DemandResult | None = None
) -> str:
    """`_result` lets callers that also need indhor.py's output (e.g. "generate all") pass an
    already-computed demand_calc result instead of paying for the ~10s computation twice."""
    result = _result if _result is not None else demand_calc.compute(session, case_id)
    buses = session.scalars(
        select(Bus).where(Bus.case_id == case_id).order_by(Bus.num_bar)
    ).all()
    demand_bus_ids = {bus_id for (bus_id, _num_blo) in result.bar_block_mw}

    # plpdem.dat's "Mes" column is per-BLOCK but the VBA writer derives it from that block's
    # stage's own calendar month (fiscal) uniformly across every block in that stage.
    stage_by_id = {s.id: s for s in session.scalars(select(Stage).where(Stage.case_id == case_id))}
    month_by_num_blo: dict[int, int] = {
        b.num_blo: fiscal_month(stage_by_id[b.stage_id].month)
        for b in session.scalars(select(Block).where(Block.case_id == case_id))
    }

    w = DatWriter()
    w.comment("Archivo de demandas por barra (plpdem.dat)")
    w.comment("Numero de barras")
    w.fields(len(buses))
    for bus in buses:
        w.comment("Nombre de la Barra")
        w.fields(quote(bus.name))
        w.comment("Numero de Demandas")
        if bus.id in demand_bus_ids:
            w.fields(f"{result.num_blo_total:03d}")
            w.comment("Mes  Etapa   Demanda")
            for num_blo in range(1, result.num_blo_total + 1):
                mw = result.bar_block_mw.get((bus.id, num_blo), 0.0)
                w.fields(
                    f"{month_by_num_blo.get(num_blo, 0):02d}",
                    f"{num_blo:03d}",
                    number(mw, 2),
                )
        else:
            w.fields(0)
    return w.render()
