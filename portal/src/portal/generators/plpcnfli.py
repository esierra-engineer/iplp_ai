"""plpcnfli.dat — transmission line config. See scratchpad spec: static_formats.md#plpcnfli.dat.

Always emits the 11-field (non-HVDC) record shape to match this case's current golden file — see
the spec's note on the reader's format auto-detect: mixing 11- and 12-field rows in one file breaks
parsing, so a case that actually needs the HVDC flag column must switch every row at once (a Phase-7
concern, not handled here).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Line, LineConfig
from .common import DatWriter, logical, number, quote


def generate(session: Session, case_id: int) -> str:
    config = session.get(LineConfig, case_id)
    lines = session.scalars(
        select(Line).where(Line.case_id == case_id).order_by(Line.id)
    ).all()

    w = DatWriter()
    w.comment("Archivo de configuracion de lineas (plpcnfli.dat)")
    w.comment("Num.Lineas   Modela Perdidas  Perd.en.ERM   Ang. de Ref.")
    w.fields(
        len(lines),
        logical(config.models_losses_globally if config else True),
        quote(config.loss_model_in_erm if config else "M"),
        "1000.d0",
    )
    w.comment(
        "Caracteristicas de las Lineas"
    )
    w.comment(
        "Nombre                                              F.Max. A-B F.Max. B-A  Barra A  "
        "Barra B   Tension  R(Ohm)  X(ohm)   Mod.Perd.  Num.Tramos   Operativa"
    )
    for line in lines:
        w.fields(
            quote(line.name),
            number(line.capacity_ab, 1),
            number(line.capacity_ba, 1),
            line.bus_from.num_bar,
            line.bus_to.num_bar,
            number(line.voltage_kv, 1),
            number(line.resistance, 3),
            number(line.reactance, 3),
            logical(line.models_losses),
            line.num_segments,
            logical(line.operational),
        )
    return w.render()
