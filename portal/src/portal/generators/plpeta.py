"""plpeta.dat — stage ('Etapa') calendar. See scratchpad spec: block_dependant_formats.md#plpeta.dat.

Writes the file's "Ano"/"Mes" columns as the solver's April-start FISCAL year/month, derived here
from the calendar (year, month) stored on Stage — see db/models.py's Stage docstring for why these
two representations differ and the cross-check that pinned down the formula.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Stage
from .common import DatWriter, logical, number, quote


def _fiscal_year_month(year: int, month: int, start_year: int, start_month: int) -> tuple[int, int]:
    """April-start fiscal (year_index, month_index), 1-based, relative to the case's first stage."""
    fiscal_month = month - 3 if month >= 4 else month + 9

    def fiscal_year_key(y: int, m: int) -> int:
        return y if m >= 4 else y - 1

    fiscal_year_index = fiscal_year_key(year, month) - fiscal_year_key(start_year, start_month) + 1
    return fiscal_year_index, fiscal_month


def generate(session: Session, case_id: int) -> str:
    stages = session.scalars(
        select(Stage).where(Stage.case_id == case_id).order_by(Stage.num_eta)
    ).all()

    w = DatWriter()
    w.comment("Archivo con la duracion de las etapas")
    w.comment("Etapas")
    w.fields(len(stages), quote("H"))
    w.comment("Ano  Mes  Etapa FDesh   NHoras    FactTasa    TipoEtapa")

    if not stages:
        return w.render()

    start_year, start_month = stages[0].year, stages[0].month
    for s in stages:
        fiscal_year, fiscal_month = _fiscal_year_month(s.year, s.month, start_year, start_month)
        w.fields(
            f"{fiscal_year:03d}",
            f"{fiscal_month:03d}",
            f"{s.num_eta:03d}",
            logical(s.hydro_dependent),
            s.duration,
            number(s.rate_factor),
            quote(s.label),
        )
    return w.render()
