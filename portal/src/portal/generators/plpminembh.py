"""plpminembh.dat — reservoir minimum volume with slack cost, by stage. See scratchpad spec:
block_dependant_formats.md#plpminembh.dat. No Mes column (unlike plpmanem.dat). `level_min` is
converted from Cota to volume via the ported Vol_<Name> curves here, at generation time — see
db/models.py's ReservoirMinVolumeSlack docstring for why it's stored in raw sheet units.

The Vol_<Name> curves return values in the same raw scale as the Centrales sheet's own volume
columns; this file's VolMin token wants that divided by 1000 (confirmed empirically against
COLBUN: curve output 1001.0194607 vs golden file 1.0010195) — a plain /1000 here, NOT the
f_esc-dependent formula plpcnfce.dat's embalse volumes needed (see generators/plpcnfce.py) —
different files, different conventions.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..curves.reservoir_volume import volume_from_level
from ..db.models import Plant, ReservoirMinVolumeSlack
from .common import DatWriter, number, quote


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(ReservoirMinVolumeSlack)
        .where(ReservoirMinVolumeSlack.case_id == case_id)
        .order_by(ReservoirMinVolumeSlack.plant_id, ReservoirMinVolumeSlack.stage_start)
    ).all()
    by_plant: dict[Plant, list[ReservoirMinVolumeSlack]] = defaultdict(list)
    for r in rows:
        by_plant[r.plant].append(r)

    w = DatWriter()
    w.comment("Archivo de minimos de embalses con holgura (plpminembh.dat)")
    w.comment("Numero de embalses con mantenimientos")
    w.fields(len(by_plant))
    for plant, ranges in by_plant.items():
        w.comment("Nombre del embalse")
        w.fields(quote(plant.name))
        n_eta = sum(r.stage_end - r.stage_start + 1 for r in ranges)
        w.comment("Numero de Etapas con vmin")
        w.fields(n_eta)
        w.comment("Etapa     VolMin     Costo")
        for r in ranges:
            vol_min = volume_from_level(plant.name, r.level_min) / 1000.0
            for num_eta in range(r.stage_start, r.stage_end + 1):
                w.fields(f"{num_eta:03d}", number(vol_min, 7), number(r.cost, 4))
    return w.render()
