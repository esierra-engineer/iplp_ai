"""plpmanbat.dat — battery maintenance by block. Filename per the user's 2026-08-30 ruling: the
Fortran source (genpdbaterias.f) is the rule over the checked-in sample's mismatched
'plpmantbat.dat' name. No Excel source (see db/models.py's BatteryMaintenance docstring) —
BatteryMaintenance rows were themselves bootstrapped from the golden file at import time."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Battery, BatteryMaintenance
from .common import DatWriter, number


def generate(session: Session, case_id: int) -> str:
    rows = session.scalars(
        select(BatteryMaintenance)
        .where(BatteryMaintenance.case_id == case_id)
        .order_by(BatteryMaintenance.battery_id, BatteryMaintenance.block_start)
    ).all()
    by_battery: dict[Battery, list[BatteryMaintenance]] = defaultdict(list)
    for r in rows:
        by_battery[r.battery].append(r)

    w = DatWriter()
    w.comment("Archivo de mantenimientos de baterias (plpmanbat.dat)")
    w.comment("numero de baterias con matenimientos")
    w.fields(len(by_battery))
    for battery, ranges in by_battery.items():
        w.comment("Nombre de la bateria")
        w.fields(battery.plant.name)
        n_blo = sum(r.block_end - r.block_start + 1 for r in ranges)
        w.comment("Numero de Bloques e Intervalos")
        w.fields(n_blo)
        w.comment("Bloque  EMin    EMax")
        for r in ranges:
            for num_blo in range(r.block_start, r.block_end + 1):
                w.fields(f"{num_blo:03d}", number(r.e_min, 2), number(r.e_max, 2))
    return w.render()
