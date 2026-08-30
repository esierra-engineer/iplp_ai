"""plprun.dat — hot-start control (one row per case, fully optional at the solver level). See
scratchpad spec: static_formats.md#plprun.dat."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.models import RunParams
from .common import DatWriter


def generate(session: Session, case_id: int) -> str:
    p = session.get(RunParams, case_id)
    w = DatWriter()
    w.comment("Archivo que controla la partida en caliente")
    w.comment("Nombre del archivo")
    w.fields(p.plane_file)
    w.comment("Rango de iteraciones a incluir (beg, end)")
    w.fields(p.iter_beg, p.iter_end)
    w.comment("Open Mode (0, no cortes. 1, cortes plpplanos.csv. 2, append cortes a archivo)")
    w.fields(p.open_mode)
    return w.render()
