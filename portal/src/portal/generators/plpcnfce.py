"""plpcnfce.dat — plant fleet configuration. See scratchpad spec: static_formats.md#plpcnfce.dat.

The largest and most structurally complex file in the whole project (23,723 lines in this case's
golden sample): 6 type-blocks (Embalse, Serie, Pasada, Termica, Bateria, Falla), each writing 4
data lines per plant whose *field count itself varies by block* — see the field-count table below,
cross-read directly from leecnfce.f rather than inferred from the file alone:

                          line1 (id/flags)   line2 (interval)   line3 (cost)   line4 (economics)
    EMBALSE                8 (has EstocFIndep)  4 (has Vert)       3              13 (has Emb* fields)
    SERIE                  8 (has EstocFIndep)  4 (has Vert)       3              7
    PASADA                 8 (has EstocFIndep)  2 (no Vert)        3              7
    TERMICA                7 (no EstocFIndep)   2 (no Vert)        3              6
    BATERIA / FALLA        7 (no EstocFIndep)   2 (no Vert)        3              6

'E' vs 'A' (Embalse/EmbalseAux) and 'S' vs 'R' (Serie/Riego) are NOT stored as separate plant_types
here — they're derived at write time from whether bus_id is set, exactly matching leecnfce.f's own
`IF (CenGBar(ICen) .EQ. 0) THEN ... ELSE ...` classification. The header line's constant flags
(Interm/Min.Tec./Cos.Arr.Det./FFaseSinMT/EtapaCambioFase) are hardcoded — confirmed uniformly
False/0 across this case's entire golden file, and the VBA writer hardcodes them too (never reads
them from any sheet).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Plant
from .common import DatWriter, logical, number, quote


def _plants_by_type(session: Session, case_id: int, plant_type: str) -> list[Plant]:
    return session.scalars(
        select(Plant)
        .where(Plant.case_id == case_id, Plant.plant_type == plant_type)
        .order_by(Plant.cen_ind)
    ).all()


def _write_record(w: DatWriter, p: Plant, *, has_estoc: bool, has_vert: bool, econ_len: int) -> None:
    w.comment("-")
    line1 = [p.cen_ind, quote(p.name), p.cen_ipot, logical(p.min_tec), logical(p.inter), logical(p.fcad), logical(p.mttd_hrz)]
    if has_estoc:
        line1.append(logical(bool(p.estoc_findep)))
    w.fields(*line1)

    # pot_min/pot_max/vert_*/cos_var/cau_afl are all rounded to 1 decimal in the golden file even
    # where the Centrales sheet carries more precision (confirmed across the whole 2964-plant file:
    # every value has at most 1 decimal digit) — the VBA writer evidently rounds these on output,
    # so this generator matches that rather than preserving the sheet's full precision.
    w.comment("-")
    line2 = [number(p.pot_min, 1), number(p.pot_max, 1)]
    if has_vert:
        line2 += [number(p.vert_min or 0.0, 1), number(p.vert_max or 0.0, 1)]
    w.fields(*line2)

    w.comment("-")
    w.fields(number(p.cost_arranque, 1), number(p.cost_detencion, 1), logical(p.on_flag))

    w.comment("-")
    line4 = [
        number(p.cos_var, 1),
        number(p.rendimiento, 3),
        p.bus.num_bar if p.bus else 0,
        p.downstream_gen_plant.cen_ind if p.downstream_gen_plant else 0,
        p.downstream_vert_plant.cen_ind if p.downstream_vert_plant else 0,
        number(p.p_ini, 2),
    ]
    if econ_len >= 7:
        line4.append(number(p.cau_afl or 0.0, 1))
    if econ_len >= 13:
        res = p.reservoir
        # Reservoir.vol_* are stored in the sheet's own units (hm3); the file token is
        # sheet_value * 1e6 / f_esc (empirically confirmed against two embalses with different
        # f_esc — LMAULE's 1e9 and CIPRESES' 1e8 both check out against this exact formula, not a
        # fixed /1000). Reading leecnfce.f shows why: the solver internally computes
        # `file_value * f_esc / 1000`, so f_esc's only effect is on the file token's own magnitude
        # — the two divisions cancel and the internal value the solver actually uses is always
        # `sheet_value * 1000`, independent of which f_esc was chosen.
        scale = 1e6 / res.f_esc
        line4 += [
            number(res.vol_ini * scale, 7),
            number(res.vol_fin * scale, 7),
            number(res.vol_min * scale, 7),
            number(res.vol_max * scale, 7),
            number(res.f_esc, 0),
            logical(res.cfue),
        ]
    w.fields(*line4)


def generate(session: Session, case_id: int) -> str:
    embalse = _plants_by_type(session, case_id, "EMBALSE")
    serie = _plants_by_type(session, case_id, "SERIE")
    pasada = _plants_by_type(session, case_id, "PASADA")
    termica = _plants_by_type(session, case_id, "TERMICA")
    bateria = _plants_by_type(session, case_id, "BATERIA")
    falla = _plants_by_type(session, case_id, "FALLA")
    n_central = len(embalse) + len(serie) + len(pasada) + len(termica) + len(bateria) + len(falla)

    w = DatWriter()
    w.comment("Archivo de configuracion de las centrales (plpcnfce.dat)")
    w.comment("Num.Centrales  Num.Embalses Num.Serie Num.Fallas Num.Pas.Pur. Num.BAT")
    w.fields(n_central, len(embalse), len(serie), len(falla), len(pasada), len(bateria))
    w.comment("Interm Min.Tec. Cos.Arr.Det. FFaseSinMT EtapaCambioFase")
    # Hardcoded — confirmed always F/F/F/F/00 in this case and never read from any sheet by the
    # VBA writer either (see module docstring).
    w.fields(logical(False), logical(False), logical(False), logical(False), "00")

    w.comment("Caracteristicas Centrales")
    w.comment("Centrales de Embalse")
    for p in embalse:
        _write_record(w, p, has_estoc=True, has_vert=True, econ_len=13)

    w.comment("Centrales Serie Hidraulica")
    for p in serie:
        _write_record(w, p, has_estoc=True, has_vert=True, econ_len=7)

    w.comment("Centrales Pasada Puras")
    for p in pasada:
        _write_record(w, p, has_estoc=True, has_vert=False, econ_len=7)

    w.comment("Centrales Termicas o Embalses Equivalentes,FV,EO,CS")
    for p in termica:
        _write_record(w, p, has_estoc=False, has_vert=False, econ_len=6)

    w.comment("Baterias y Fallas")
    for p in bateria:
        _write_record(w, p, has_estoc=False, has_vert=False, econ_len=6)
    for p in falla:
        _write_record(w, p, has_estoc=False, has_vert=False, econ_len=6)

    return w.render()
