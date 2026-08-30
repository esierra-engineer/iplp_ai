"""indhor.csv — calendar hour -> block index lookup. Not read by the solver itself (confirmed: no
Fortran reader references it — see block_dependant_formats.md's summary), but produced by the same
VBA writer as plpdem.dat and potentially used by other tooling, so generated for parity.

Plain CSV, not a list-directed .dat file — no comment-line/header-count conventions apply here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import demand_calc


def generate(
    session: Session, case_id: int, _result: demand_calc.DemandResult | None = None
) -> str:
    """`_result` lets callers that also need plpdem.py's output (e.g. "generate all") pass an
    already-computed demand_calc result instead of paying for the ~10s computation twice."""
    result = _result if _result is not None else demand_calc.compute(session, case_id)
    lines = ["Año,Mes,Dia,Hora,Bloque"]
    for year, month, day, hour, num_blo in result.hour_to_block:
        lines.append(f"{year},{month},{day},{hour},{num_blo}")
    return "\n".join(lines) + "\n"
