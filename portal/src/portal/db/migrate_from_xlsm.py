"""One-time importer: openpyxl (+ the current golden .dat files) -> SQLite, for a new Case.

Phase 1 scope only: buses (Barras), lines (Líneas), the stage calendar (Etapas), and the three
solver-control files (plpmat.dat/plpdeb.dat/plprun.dat).

Known bootstrap limitation (documented, not hidden): two pieces of Phase 1 data are NOT derived
from the .xlsm because doing so requires porting VBA logic outside this phase's scope:

- Stage.hydro_dependent (FDesh) and Stage.rate_factor (FactTasa) are not plain Etapas-sheet
  columns — FactTasa in particular is a compounding per-stage discount factor. This importer reads
  both straight from the case's existing dat/block_dependant/plpeta.dat (the current, authoritative
  output for this case) rather than re-deriving them, since that derivation isn't ported yet.
- Block durations (plpblo.dat) come from the same kind of load-duration-curve algorithm
  (`Rutina05.Curva_de_Carga_Mod`, see the plan's VBA module map) that is out of scope for Phase 1.
  This importer reads block durations straight from the case's existing dat/block_dependant/plpblo.dat.
- plpmat.dat/plpdeb.dat/plprun.dat aren't clearly Excel-sourced at all (no sheet reference was found
  for them in the VBA map) — imported straight from dat/static/.

Both are legitimate for a *migration* importer (its job is exactly "seed the DB from whatever is
currently authoritative for this case"), but a from-scratch new case created only in the web UI,
with no pre-existing .dat files, will need those derivations ported before Phase 1's generators can
produce correct values for it. Track that as follow-up work, not silently assumed solved.

Phase 2 (plant fleet) adds a similar situation, worth calling out separately since it's not a
scoping shortcut but a genuine absence: **no VBA writer for plpcenre.dat or plpcenpmax.dat was
found in either xla workbook** (searched both). Those two files' reservoir rating-curve data has no
Excel source at all — bootstrapped from the golden files here, same mechanism as above. Separately,
plpcnfce.dat's per-embalse `EmbFEsc` (scale factor) also has no Centrales-sheet column (confirmed by
cross-checking real values against the parsed golden file) and is bootstrapped the same way; every
other plpcnfce.dat field below (including the header's 5 constant flags, and 9 per-plant fields
confirmed uniform-constant across all 2964 plants in this case: cen_ipot, min_tec, inter, fcad,
mttd_hrz, cost_arranque, cost_detencion, on_flag, p_ini) comes straight from the Centrales sheet —
see `_import_plants`'s column-mapping comment, empirically validated against the golden file's
actual values (not just the sheet's header labels, which are ambiguous in a couple of spots).
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
from sqlalchemy.orm import Session

from ..dat_readers import (
    parse_plpblo,
    parse_plpcenbat,
    parse_plpcenpmax,
    parse_plpcenre,
    parse_plpcnfce,
    parse_plpdeb,
    parse_plpeta,
    parse_plpmat,
    parse_plprun,
)
from .models import (
    Battery,
    BatteryInjector,
    Bus,
    Case,
    DebugParams,
    Line,
    LineConfig,
    MathParams,
    Plant,
    Reservoir,
    ReservoirPmaxCurve,
    ReservoirPmaxSegment,
    ReservoirYieldCurve,
    ReservoirYieldSegment,
    RunParams,
    Stage,
    Block,
)

# Centrales sheet "Tipo de Central" single-letter code -> Plant.plant_type. 'E'/'A' and 'S'/'R' each
# collapse to one plant_type; which sub-code a plant gets at generation time is derived from
# bus_id (see generators/plpcnfce.py), matching leecnfce.f's own CenGBar==0 classification exactly.
# 'X' (fuera de servicio) plants are not imported at all — matches the VBA writer's own count.
_CENTRALES_TYPE_MAP = {
    "E": "EMBALSE",
    "S": "SERIE",
    "R": "SERIE",
    "P": "PASADA",
    "T": "TERMICA",
    "BAT": "BATERIA",
    "F": "FALLA",
}


def import_case(
    session: Session,
    *,
    case_name: str,
    xlsm_path: Path,
    dat_static_dir: Path,
    dat_block_dependant_dir: Path,
    description: str | None = None,
) -> Case:
    wb = openpyxl.load_workbook(xlsm_path, data_only=True, keep_vba=False)

    case = Case(name=case_name, description=description)
    session.add(case)
    session.flush()  # assign case.id

    bus_by_num = _import_buses(session, case, wb)
    stage_by_num = _import_stages(session, case, wb, dat_block_dependant_dir)
    _import_blocks(session, case, stage_by_num, dat_block_dependant_dir)
    _import_lines(session, case, bus_by_num, wb)
    _import_solver_params(session, case, dat_static_dir)

    plant_by_name = _import_plants(session, case, bus_by_num, wb, dat_static_dir)
    _import_reservoir_curves(session, case, plant_by_name, dat_static_dir)
    _import_batteries(session, case, bus_by_num, plant_by_name, wb)

    return case


def _import_buses(session: Session, case: Case, wb) -> dict[int, Bus]:
    """Barras sheet: header row 5 ('Nº', 'BARRA'), data from row 6."""
    ws = wb["Barras"]
    bus_by_num: dict[int, Bus] = {}
    row = 6
    while True:
        num = ws.cell(row, 1).value
        name = ws.cell(row, 2).value
        if num is None or name is None:
            break
        bus = Bus(case_id=case.id, num_bar=int(num), name=str(name))
        session.add(bus)
        bus_by_num[int(num)] = bus
        row += 1
    session.flush()
    return bus_by_num


def _import_stages(session: Session, case: Case, wb, dat_block_dependant_dir: Path) -> dict[int, Stage]:
    """Etapas sheet: header row 4 ('Etapa','Inicial','Nº Días','Final','Año','Mes','Nº Bloques'),
    data from row 5. FDesh/FactTasa are bootstrapped from the golden plpeta.dat (see module docstring)."""
    ws = wb["Etapas"]
    golden = parse_plpeta((dat_block_dependant_dir / "plpeta.dat").read_text(encoding="latin-1"))
    golden_by_num = {s["num_eta"]: s for s in golden["stages"]}

    stage_by_num: dict[int, Stage] = {}
    row = 5
    while True:
        num_eta = ws.cell(row, 1).value
        inicial = ws.cell(row, 2).value
        n_dias = ws.cell(row, 3).value
        n_bloques = ws.cell(row, 7).value
        if num_eta is None or inicial is None:
            break
        num_eta = int(num_eta)
        g = golden_by_num.get(num_eta, {})
        stage = Stage(
            case_id=case.id,
            num_eta=num_eta,
            year=inicial.year,
            month=inicial.month,
            hydro_dependent=g.get("hydro_dependent", False),
            duration=int(n_dias) * 24,
            rate_factor=g.get("rate_factor", 1.0),
            label=f"{int(n_bloques)} Bloques",
        )
        session.add(stage)
        stage_by_num[num_eta] = stage
        row += 1
    session.flush()
    return stage_by_num


def _import_blocks(
    session: Session, case: Case, stage_by_num: dict[int, Stage], dat_block_dependant_dir: Path
) -> None:
    """plpblo.dat block durations, bootstrapped straight from the golden file (see module docstring)."""
    golden = parse_plpblo((dat_block_dependant_dir / "plpblo.dat").read_text(encoding="latin-1"))
    for b in golden["blocks"]:
        stage = stage_by_num[b["num_eta"]]
        session.add(
            Block(
                case_id=case.id,
                num_blo=b["num_blo"],
                stage_id=stage.id,
                duration=b["duration"],
                year=stage.year,
                month=stage.month,
                label=f"Bloque {b['num_blo']:02d}",
            )
        )
    session.flush()


def _import_lines(session: Session, case: Case, bus_by_num: dict[int, Bus], wb) -> None:
    """Líneas sheet: header row 5, data from row 6 (see column mapping in generators/plpcnfli.py)."""
    ws = wb["Líneas"]
    session.add(
        LineConfig(
            case_id=case.id,
            models_losses_globally=bool(ws.cell(1, 13).value),
            loss_model_in_erm=str(ws.cell(2, 13).value),
        )
    )
    row = 6
    while True:
        name = ws.cell(row, 2).value
        if name is None:
            break
        bus_a = bus_by_num[int(ws.cell(row, 3).value)]
        bus_b = bus_by_num[int(ws.cell(row, 4).value)]
        session.add(
            Line(
                case_id=case.id,
                name=str(name),
                bus_from_id=bus_a.id,
                bus_to_id=bus_b.id,
                capacity_ab=float(ws.cell(row, 5).value),
                capacity_ba=float(ws.cell(row, 6).value),
                voltage_kv=float(ws.cell(row, 7).value),
                resistance=float(ws.cell(row, 10).value),
                reactance=float(ws.cell(row, 11).value),
                models_losses=bool(ws.cell(row, 12).value),
                num_segments=int(ws.cell(row, 13).value),
                operational=bool(ws.cell(row, 14).value),
                is_hvdc=bool(ws.cell(row, 15).value) if ws.cell(row, 15).value is not None else None,
            )
        )
        row += 1
    session.flush()


def _import_solver_params(session: Session, case: Case, dat_static_dir: Path) -> None:
    """plpmat.dat/plpdeb.dat/plprun.dat: no confirmed Excel source (see module docstring) —
    bootstrapped straight from the golden static files."""
    mat = parse_plpmat((dat_static_dir / "plpmat.dat").read_text(encoding="latin-1"))
    deb = parse_plpdeb((dat_static_dir / "plpdeb.dat").read_text(encoding="latin-1"))
    run = parse_plprun((dat_static_dir / "plprun.dat").read_text(encoding="latin-1"))
    session.add(MathParams(case_id=case.id, **mat))
    session.add(DebugParams(case_id=case.id, **deb))
    session.add(RunParams(case_id=case.id, **run))


def _import_plants(
    session: Session, case: Case, bus_by_num: dict[int, Bus], wb, dat_static_dir: Path
) -> dict[str, Plant]:
    """Centrales sheet: header rows 4-5, data from row 6. Column mapping below was derived from the
    sheet's own header labels, then EMPIRICALLY VALIDATED by cross-checking real values (cen_ind,
    name, bus, downstream references, volumes, etc.) for one plant of each type against the parsed
    golden plpcnfce.dat — not assumed correct from the labels alone, which are ambiguous for the
    embalse-only volume columns (two similarly-named column groups exist; only one is the one
    leecnfce.f actually reads). See the plan/session notes for the full trace.

    col 1  = cen_ind ("INDICE")              col 9  = cfue ("Función Costo Futuro", Embalse only)
    col 2  = name                            col 12 = cau_afl ("Afluente Primera Semana")
    col 3  = type letter                     col 13 = estoc_findep ("Independencia Hidrológica")
    col 4  = cos_var ("Costo Variable")      col 23 = vol_ini ("Volumen del embalse hm3" Inicial)
    col 5  = rendimiento                     col 24 = vol_fin (... Final)
    col 6  = bus ("Conectada a la Barra")    col 25 = vol_min (... Mínimo)
    col 7  = gen_hid ref ("Generación")      col 26 = vol_max (... Máximo)
    col 8  = vert_hid ref ("Vertimiento")    col 27 = pot_min ("Potencia Neta" Mínima)
                                              col 28 = pot_max (... Máxima)
                                              col 29 = vert_min ("Vertimiento" Mínimo)
                                              col 30 = vert_max (... Máximo)

    (col 10, "Afluente Estocástico", tracks col 13 exactly in every sample checked — could be a
    duplicate/legacy column; col 13's label is the closer semantic match to Fortran's EstocFIndep
    and is what's used here.)

    gen_hid/vert_hid are the referenced plant's cen_ind (0/blank = no downstream) — resolved to
    Plant FKs in a second pass below since a plant can reference one that appears later in the sheet.

    Reservoir.vol_ini/vol_fin/vol_min/vol_max are stored here in the sheet's own units (hm3, e.g.
    LMAULE's ~757) — the .dat file token is `sheet_value * 1e6 / f_esc` (confirmed empirically
    against two embalses with different f_esc; see generators/plpcnfce.py for the formula and why
    f_esc's effect cancels out internally regardless). Storing raw sheet units in the DB (rather
    than the file-scaled value) keeps the web UI showing the same numbers an analyst already knows
    from Excel — the scaling is purely a file-writing convention, applied only at generation time.
    """
    ws = wb["Centrales"]
    golden_femb = {
        p["name"]: p["f_esc"]
        for p in parse_plpcnfce((dat_static_dir / "plpcnfce.dat").read_text(encoding="latin-1"))["plants"]
        if p["block"] == "EMBALSE"
    }

    plant_by_name: dict[str, Plant] = {}
    plant_by_cen_ind: dict[int, Plant] = {}
    pending_refs: list[tuple[Plant, int, int]] = []  # (plant, gen_hid_ref, vert_hid_ref)

    row = 6
    while True:
        cen_ind = ws.cell(row, 1).value
        if cen_ind is None:
            break
        type_letter = str(ws.cell(row, 3).value or "").strip().upper()
        plant_type = _CENTRALES_TYPE_MAP.get(type_letter)
        if plant_type is None:  # 'X' (fuera de servicio) or unrecognized — not part of the .dat file
            row += 1
            continue

        bus_num = ws.cell(row, 6).value
        bus = bus_by_num.get(int(bus_num)) if bus_num else None

        def f(col: int) -> float:
            v = ws.cell(row, col).value
            return float(v) if v is not None else 0.0

        plant = Plant(
            case_id=case.id,
            cen_ind=int(cen_ind),
            name=str(ws.cell(row, 2).value),
            plant_type=plant_type,
            bus_id=bus.id if bus else None,
            cos_var=f(4),
            rendimiento=f(5),
            pot_min=f(27),
            pot_max=f(28),
        )
        if plant_type in ("EMBALSE", "SERIE"):
            plant.vert_min = f(29)
            plant.vert_max = f(30)
        if plant_type in ("EMBALSE", "SERIE", "PASADA"):
            plant.cau_afl = f(12)
            plant.estoc_findep = bool(ws.cell(row, 13).value)
        session.add(plant)
        session.flush()  # assign plant.id before Reservoir/self-FK resolution below

        if plant_type == "EMBALSE":
            session.add(
                Reservoir(
                    plant_id=plant.id,
                    vol_ini=f(23),
                    vol_fin=f(24),
                    vol_min=f(25),
                    vol_max=f(26),
                    f_esc=golden_femb.get(plant.name, 1.0),
                    cfue=bool(ws.cell(row, 9).value),
                )
            )

        plant_by_name[plant.name] = plant
        plant_by_cen_ind[plant.cen_ind] = plant
        gen_ref = ws.cell(row, 7).value
        vert_ref = ws.cell(row, 8).value
        pending_refs.append((plant, int(gen_ref) if gen_ref else 0, int(vert_ref) if vert_ref else 0))
        row += 1

    session.flush()
    for plant, gen_ref, vert_ref in pending_refs:
        if gen_ref:
            target = plant_by_cen_ind.get(gen_ref)
            if target is None:
                print(
                    f"import_case: warning, {plant.name!r} references downstream-gen cen_ind "
                    f"{gen_ref} which isn't an imported (non-'X') plant — leaving unset."
                )
            else:
                plant.downstream_gen_plant_id = target.id
        if vert_ref:
            target = plant_by_cen_ind.get(vert_ref)
            if target is None:
                print(
                    f"import_case: warning, {plant.name!r} references downstream-vert cen_ind "
                    f"{vert_ref} which isn't an imported (non-'X') plant — leaving unset."
                )
            else:
                plant.downstream_vert_plant_id = target.id
    session.flush()

    return plant_by_name


def _import_reservoir_curves(
    session: Session, case: Case, plant_by_name: dict[str, Plant], dat_static_dir: Path
) -> None:
    """plpcenre.dat/plpcenpmax.dat: no confirmed Excel/VBA source at all (see module docstring) —
    bootstrapped straight from the golden static files."""
    cenre = parse_plpcenre((dat_static_dir / "plpcenre.dat").read_text(encoding="latin-1"))
    for r in cenre["reservoirs"]:
        curve = ReservoirYieldCurve(
            case_id=case.id,
            plant_id=plant_by_name[r["plant_name"]].id,
            reservoir_plant_id=plant_by_name[r["reservoir_name"]].id,
            avg_yield=r["avg_yield"],
        )
        session.add(curve)
        session.flush()
        for seg in r["segments"]:
            session.add(
                ReservoirYieldSegment(
                    curve_id=curve.id,
                    ind=seg["ind"],
                    volume=seg["volume"],
                    slope=seg["slope"],
                    constant=seg["constant"],
                    scale=seg["scale"],
                )
            )

    cenpmax = parse_plpcenpmax((dat_static_dir / "plpcenpmax.dat").read_text(encoding="latin-1"))
    for r in cenpmax["reservoirs"]:
        curve = ReservoirPmaxCurve(
            case_id=case.id,
            plant_id=plant_by_name[r["plant_name"]].id,
            reservoir_plant_id=plant_by_name[r["reservoir_name"]].id,
        )
        session.add(curve)
        session.flush()
        for seg in r["segments"]:
            session.add(
                ReservoirPmaxSegment(
                    curve_id=curve.id, volume=seg["volume"], slope=seg["slope"], constant=seg["constant"]
                )
            )
    session.flush()


def _import_batteries(
    session: Session, case: Case, bus_by_num: dict[int, Bus], plant_by_name: dict[str, Plant], wb
) -> None:
    """Baterias sheet: header row 6, data from row 7 (INDICE, BATERIAS, Conectada a la Barra,
    Rendimiento de Descarga, Capacidad Mínima/Máxima, ..., Central de Carga, Batería objetivo,
    Rendimiento de Carga). This case has exactly one injector per battery (col 9), but the schema
    (and plpcenbat.dat's own format) supports more — extend this loop if a future case needs it."""
    ws = wb["Baterias"]
    row = 7
    while True:
        bat_ind = ws.cell(row, 1).value
        name = ws.cell(row, 2).value
        if bat_ind is None or name is None:
            break
        plant = plant_by_name.get(str(name))
        if plant is None:
            row += 1
            continue  # no matching BATERIA-type row in Centrales — skip rather than guess
        battery = Battery(
            case_id=case.id,
            plant_id=plant.id,
            bat_ind=int(bat_ind),
            bus_id=bus_by_num[int(ws.cell(row, 3).value)].id,
            discharge_loss_factor=float(ws.cell(row, 4).value),
            capacity_min=float(ws.cell(row, 5).value),
            capacity_max=float(ws.cell(row, 6).value),
        )
        session.add(battery)
        session.flush()
        injector_name = ws.cell(row, 9).value
        if injector_name is not None:
            session.add(
                BatteryInjector(
                    battery_id=battery.id,
                    name=str(injector_name),
                    loss_factor=float(ws.cell(row, 11).value),
                )
            )
        row += 1
    session.flush()
