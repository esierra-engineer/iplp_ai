"""plplajam.dat — Laja basin convention. See scratchpad spec: static_formats.md#plplajam.dat and
db/models.py's Phase 6 section docstring for why this is a verbatim line replay rather than
individually-typed fields (same reasoning as plpmaulen.py)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import BasinConventionLine


def generate(session: Session, case_id: int) -> str:
    lines = session.scalars(
        select(BasinConventionLine)
        .where(BasinConventionLine.case_id == case_id, BasinConventionLine.convention == "LAJA")
        .order_by(BasinConventionLine.line_order)
    ).all()
    return "".join(line.text + "\n" for line in lines)
