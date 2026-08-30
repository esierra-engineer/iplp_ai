"""Permissive, record-structure-aware parsers for reading existing .dat files.

Two consumers share this module:

1. ``tests/parsers.py`` (re-exporting from here) — validates generated .dat files. Per the
   project's stated validation criterion (and confirmed by the Fortran spec research): what matters
   in a .dat file is one record per line, the right number of fields per row, and comment lines
   being ignorable filler — not byte-identical formatting. So instead of diffing generated output
   against the golden files in `dat/` byte-for-byte, each `test_<file>.py` parses both with the
   matching `parse_<file>()` function here (mirroring the actual Fortran reader's record structure)
   and compares the resulting field values.
2. ``db.migrate_from_xlsm`` — bootstraps DB fields that aren't yet derivable from the .xlsm (see
   that module's docstring) by reading them straight out of the case's existing golden .dat files.

Tokenization mirrors Fortran list-directed READ: values are separated by whitespace and/or commas,
quoted strings (`'like this'`) are one token including embedded spaces, and floats accept Fortran's
`d`/`D` exponent letter in addition to `e`/`E`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


def tokenize(line: str) -> list[str]:
    """Split one physical line into list-directed-READ-style tokens (quotes kept, so callers can
    tell a quoted empty string '' apart from a genuinely absent token)."""
    tokens: list[str] = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c in " \t,":
            i += 1
            continue
        if c == "'":
            j = line.find("'", i + 1)
            j = j if j != -1 else n - 1
            tokens.append(line[i : j + 1])
            i = j + 1
        else:
            j = i
            while j < n and line[j] not in " \t,":
                j += 1
            tokens.append(line[i:j])
            i = j
    return tokens


_FORTRAN_EXP = re.compile(r"[dD]")


def parse_float(token: str) -> float:
    return float(_FORTRAN_EXP.sub("e", token))


def parse_int(token: str) -> int:
    return int(token)


def parse_bool(token: str) -> bool:
    t = token.strip().strip(".").upper()
    if t in ("T", "TRUE"):
        return True
    if t in ("F", "FALSE"):
        return False
    raise ValueError(f"not a Fortran logical literal: {token!r}")


def parse_name(token: str) -> str:
    """Strip surrounding quotes if present; bare (unquoted) tokens are returned as-is
    (plpcenbat.dat uses unquoted bareword names — see spec)."""
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1]
    return token


@dataclass
class RecordReader:
    """Sequential line cursor over a .dat file's text, one record (line) at a time."""

    lines: list[str]
    pos: int = field(default=0)

    @classmethod
    def from_text(cls, text: str) -> "RecordReader":
        return cls(lines=text.splitlines())

    def skip(self, n: int = 1) -> None:
        """Skip n header/comment lines — content is never inspected, only the count matters."""
        self.pos += n

    def next_line(self) -> str:
        line = self.lines[self.pos]
        self.pos += 1
        return line

    def next_tokens(self) -> list[str]:
        return tokenize(self.next_line())

    def at_end(self) -> bool:
        return self.pos >= len(self.lines)

    def peek_is_comment(self) -> bool:
        """True if the reader is exhausted, or the current (not-yet-consumed) line starts with
        '#', or is blank (trailing blank lines at EOF are common and never carry data). Since the
        actual Fortran readers never check this (see module docstring) it must never be used to
        parse a real .dat file the same way the solver does — only as a best-effort
        self-correction when bootstrapping from a file that turns out to have a count/content
        mismatch (see parse_plpmanbat)."""
        if self.at_end():
            return True
        stripped = self.lines[self.pos].strip()
        return stripped == "" or stripped.startswith("#")


# ---------------------------------------------------------------------------------------------
# Phase 1 file parsers
# ---------------------------------------------------------------------------------------------


def parse_plpbar(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_bar = parse_int(r.next_tokens()[0])
    r.skip(1)
    buses = []
    for _ in range(n_bar):
        num, name = r.next_tokens()
        buses.append({"num": parse_int(num), "name": parse_name(name)})
    return {"n_bar": n_bar, "buses": buses}


def parse_plpeta(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_eta_tok, mode_tok = r.next_tokens()
    n_eta = parse_int(n_eta_tok)
    mode = parse_name(mode_tok)
    r.skip(1)
    stages = []
    for _ in range(n_eta):
        year, mes, num_eta, fdesh, nhoras, facttasa, tipo = r.next_tokens()
        stages.append(
            {
                "year": parse_int(year),
                "month": parse_int(mes),
                "num_eta": parse_int(num_eta),
                "hydro_dependent": parse_bool(fdesh),
                "duration": parse_int(nhoras),
                "rate_factor": parse_float(facttasa),
                "label": parse_name(tipo),
            }
        )
    return {"n_eta": n_eta, "mode": mode, "stages": stages}


def parse_plpblo(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_blo = parse_int(r.next_tokens()[0])
    r.skip(1)
    blocks = []
    for _ in range(n_blo):
        tokens = r.next_tokens()
        num_blo, num_eta, dur_blo = tokens[0], tokens[1], tokens[2]  # extra decorative cols ignored
        blocks.append(
            {
                "num_blo": parse_int(num_blo),
                "num_eta": parse_int(num_eta),
                "duration": parse_float(dur_blo),
            }
        )
    return {"n_blo": n_blo, "blocks": blocks}


def parse_plpcnfli(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    header = r.next_tokens()
    n_linea = parse_int(header[0])
    models_losses = parse_bool(header[1])
    loss_model = parse_name(header[2])
    ref_angle = parse_float(header[3])
    r.skip(2)
    lines = []
    for _ in range(n_linea):
        t = r.next_tokens()
        rec = {
            "name": parse_name(t[0]),
            "capacity_ab": parse_float(t[1]),
            "capacity_ba": parse_float(t[2]),
            "bus_from": parse_int(t[3]),
            "bus_to": parse_int(t[4]),
            "voltage_kv": parse_float(t[5]),
            "resistance": parse_float(t[6]),
            "reactance": parse_float(t[7]),
            "models_losses": parse_bool(t[8]),
            "num_segments": parse_int(t[9]),
            "operational": parse_bool(t[10]),
        }
        if len(t) > 11:
            rec["is_hvdc"] = parse_bool(t[11])
        lines.append(rec)
    return {
        "n_linea": n_linea,
        "models_losses_globally": models_losses,
        "loss_model_in_erm": loss_model,
        "reference_angle": ref_angle,
        "lines": lines,
    }


def parse_plpmat(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    pd_max_ite, pd_error, umb_int_conf = r.next_tokens()[:3]
    r.skip(1)
    pm_max_ite, pm_error = r.next_tokens()[:2]
    r.skip(1)
    t = r.next_tokens()
    lam, ctasa, ccaudfalla, cvert, cinter, ctrasm, fvolfin, fpreproc, fprevia = t[:9]
    r.skip(1)
    ffixtrasm, fseparafcf, fgrabacsv, fgrabares = r.next_tokens()[:4]
    r.skip(1)
    ablmax, abepsilon, numetacf = r.next_tokens()[:3]
    r.skip(1)
    fconvpgradx, fconvpvar, umbgradx, umbzspf = r.next_tokens()[:4]
    return {
        "pd_max_iter": parse_int(pd_max_ite),
        "pd_error": parse_float(pd_error),
        "umb_int_conf": parse_float(umb_int_conf),
        "pm_max_iter": parse_int(pm_max_ite),
        "pm_error": parse_float(pm_error),
        "lambda_": parse_float(lam),
        "c_tasa": parse_float(ctasa),
        "c_caudal_falla": parse_float(ccaudfalla),
        "c_vertimiento": parse_float(cvert),
        "c_inter": parse_float(cinter),
        "c_transmision": parse_float(ctrasm),
        "f_vol_fin_emb": parse_bool(fvolfin),
        "f_pre_proc": parse_bool(fpreproc),
        "f_previa": parse_bool(fprevia),
        "f_fix_trasm": parse_bool(ffixtrasm),
        "f_separa_fcf": parse_bool(fseparafcf),
        "f_graba_csv": parse_bool(fgrabacsv),
        "f_graba_res": parse_bool(fgrabares),
        "ab_max": parse_int(ablmax),
        "ab_epsilon": parse_float(abepsilon),
        "num_eta_cf": parse_int(numetacf),
        "f_conv_pgradx": parse_bool(fconvpgradx),
        "f_conv_pvar": parse_bool(fconvpvar),
        "umb_gradx": parse_float(umbgradx),
        "umb_zspf": parse_float(umbzspf),
    }


def parse_plpdeb(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    f_log = parse_bool(r.next_tokens()[0])
    r.skip(1)
    t = r.next_tokens()
    (pri_prog_din, pd_sv_fl, pm_sv_fl, f_dat_che, er_sv_fl, ps_fz_fl, ft_sv_fl, f_sv_la_ps) = t[:8]
    r.skip(1)
    t2 = r.next_tokens()
    ind_sim_imp, ind_ite_imp, f_best, ind_eta1_imp, ind_eta2_imp = t2[:5]
    return {
        "f_log": f_log,
        "pri_prog_din": parse_bool(pri_prog_din),
        "pd_sv_fl": parse_bool(pd_sv_fl),
        "pm_sv_fl": parse_bool(pm_sv_fl),
        "f_dat_che": parse_bool(f_dat_che),
        "er_sv_fl": parse_bool(er_sv_fl),
        "ps_fz_fl": parse_bool(ps_fz_fl),
        "ft_sv_fl": parse_bool(ft_sv_fl),
        "f_sv_la_ps": parse_bool(f_sv_la_ps),
        "ind_sim_imp": parse_int(ind_sim_imp),
        "ind_ite_imp": parse_int(ind_ite_imp),
        "f_best": parse_bool(f_best),
        "ind_eta1_imp": parse_int(ind_eta1_imp),
        "ind_eta2_imp": parse_int(ind_eta2_imp),
    }


# ---------------------------------------------------------------------------------------------
# Phase 3 file parsers
# ---------------------------------------------------------------------------------------------


def parse_plpdem(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_bar = parse_int(r.next_tokens()[0])
    buses = []
    for _ in range(n_bar):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_blo_dem = parse_int(r.next_tokens()[0])
        data = []
        if n_blo_dem > 0:
            r.skip(1)
            for _ in range(n_blo_dem):
                mes, num_blo, demanda = r.next_tokens()
                data.append(
                    {"mes": parse_int(mes), "num_blo": parse_int(num_blo), "demanda": parse_float(demanda)}
                )
        buses.append({"name": name, "n_blo_dem": n_blo_dem, "data": data})
    return {"n_bar": n_bar, "buses": buses}


def parse_plpcosce(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_cen = parse_int(r.next_tokens()[0])
    plants = []
    for _ in range(n_cen):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_eta = parse_int(r.next_tokens()[0])
        r.skip(1)
        data = []
        for _ in range(n_eta):
            mes, num_eta, cos_var = r.next_tokens()
            data.append(
                {"mes": parse_int(mes), "num_eta": parse_int(num_eta), "cos_var": parse_float(cos_var)}
            )
        plants.append({"name": name, "n_eta": n_eta, "data": data})
    return {"n_cen": n_cen, "plants": plants}


def parse_indhor_csv(text: str) -> list[dict]:
    lines = text.strip().splitlines()
    rows = []
    for line in lines[1:]:  # skip "Año,Mes,Dia,Hora,Bloque" header
        year, month, day, hour, num_blo = line.split(",")
        rows.append(
            {
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "hour": int(hour),
                "num_blo": int(num_blo),
            }
        )
    return rows


# ---------------------------------------------------------------------------------------------
# Phase 4 file parsers
# ---------------------------------------------------------------------------------------------


def parse_plpmance(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_cen = parse_int(r.next_tokens()[0])
    plants = []
    for _ in range(n_cen):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_blo, _num_ipot = r.next_tokens()[:2]
        n_blo = parse_int(n_blo)
        r.skip(1)
        data = []
        for _ in range(n_blo):
            mes, num_blo, npot, pot_min, pot_max = r.next_tokens()[:5]
            data.append(
                {
                    "num_blo": parse_int(num_blo),
                    "pot_min": parse_float(pot_min),
                    "pot_max": parse_float(pot_max),
                }
            )
        plants.append({"name": name, "n_blo": n_blo, "data": data})
    return {"n_cen": n_cen, "plants": plants}


def parse_plpmanli(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_lin = parse_int(r.next_tokens()[0])
    lines_ = []
    for _ in range(n_lin):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_blo = parse_int(r.next_tokens()[0])
        r.skip(1)
        data = []
        for _ in range(n_blo):
            num_blo, man_a, man_b, fope = r.next_tokens()[:4]
            data.append(
                {
                    "num_blo": parse_int(num_blo),
                    "man_a": parse_float(man_a),
                    "man_b": parse_float(man_b),
                    "operational": parse_bool(fope),
                }
            )
        lines_.append({"name": name, "n_blo": n_blo, "data": data})
    return {"n_lin": n_lin, "lines": lines_}


def parse_plpmanem(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_emb = parse_int(r.next_tokens()[0])
    reservoirs = []
    for _ in range(n_emb):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_eta = parse_int(r.next_tokens()[0])
        r.skip(1)
        data = []
        for _ in range(n_eta):
            mes, num_eta, vol_min, vol_max = r.next_tokens()[:4]
            data.append(
                {"num_eta": parse_int(num_eta), "vol_min": parse_float(vol_min), "vol_max": parse_float(vol_max)}
            )
        reservoirs.append({"name": name, "n_eta": n_eta, "data": data})
    return {"n_emb": n_emb, "reservoirs": reservoirs}


def parse_plpminembh(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_emb = parse_int(r.next_tokens()[0])
    reservoirs = []
    for _ in range(n_emb):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_eta = parse_int(r.next_tokens()[0])
        r.skip(1)
        data = []
        for _ in range(n_eta):
            num_eta, vol_min, cost = r.next_tokens()[:3]
            data.append(
                {"num_eta": parse_int(num_eta), "vol_min": parse_float(vol_min), "cost": parse_float(cost)}
            )
        reservoirs.append({"name": name, "n_eta": n_eta, "data": data})
    return {"n_emb": n_emb, "reservoirs": reservoirs}


def parse_plpmanbat(text: str) -> dict:
    """NOTE: unlike every other parser in this module, this one does NOT trust the file's own
    declared per-battery row count (`NBloMan`) — the checked-in golden `plpmantbat.dat` has at
    least one battery whose declared count (60) doesn't match its actual row count (65), a genuine
    inconsistency in that file (which has no Excel/VBA source at all — see db/models.py's
    BatteryMaintenance docstring — so there was nothing to cross-check it against before now).
    Reads rows until the next '#'-prefixed line or EOF instead, which is self-correcting for this
    file's own actual content; the real Fortran reader (genpdbaterias.f's LeeManBat) does trust the
    declared count blindly and would desync on this exact file the same way a naive port of this
    parser initially did."""
    r = RecordReader.from_text(text)
    r.skip(2)
    n_bat = parse_int(r.next_tokens()[0])
    batteries = []
    for _ in range(n_bat):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        r.next_tokens()  # declared NBloMan — read past it, but see docstring: not trusted
        r.skip(1)
        data = []
        while not r.peek_is_comment():
            ind, e_min, e_max = r.next_tokens()[:3]
            data.append({"num_blo": parse_int(ind), "e_min": parse_float(e_min), "e_max": parse_float(e_max)})
        batteries.append({"name": name, "n_blo": len(data), "data": data})
    return {"n_bat": n_bat, "batteries": batteries}


# ---------------------------------------------------------------------------------------------
# Phase 5 file parsers
#
# All four bootstrapped as data (not re-derived) per the plan's own scoping: the "ALEATORIA"
# scenario-sampling path depends on VBA's own `Rnd` PRNG, which cannot be reproduced bit-for-bit
# in Python — so these tables are imported once from the golden files and are then plain editable
# data, not something a ported algorithm recomputes.
# ---------------------------------------------------------------------------------------------


def parse_plpaflce(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_cen, n_clase = (parse_int(t) for t in r.next_tokens()[:2])
    plants = []
    for _ in range(n_cen):
        r.skip(1)
        name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_blo = parse_int(r.next_tokens()[0])
        r.skip(1)
        blocks = []
        for _ in range(n_blo):
            tokens = r.next_tokens()
            blocks.append(
                {"num_blo": parse_int(tokens[1]), "values": [parse_float(t) for t in tokens[2 : 2 + n_clase]]}
            )
        plants.append({"name": name, "n_blo": n_blo, "blocks": blocks})
    return {"n_cen": n_cen, "n_clase": n_clase, "plants": plants}


def parse_plpidsim(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_simul, n_eta_cau = (parse_int(t) for t in r.next_tokens()[:2])
    r.skip(1)
    stages = []
    for _ in range(n_eta_cau):
        tokens = r.next_tokens()
        stages.append({"num_eta": parse_int(tokens[1]), "hydro_class": [parse_int(t) for t in tokens[2:]]})
    return {"n_simul": n_simul, "n_eta_cau": n_eta_cau, "stages": stages}


def parse_plpidape(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_simul, n_eta_cau = (parse_int(t) for t in r.next_tokens()[:2])
    simulations = []
    for _ in range(n_simul):
        r.skip(1)
        stages = []
        for _ in range(n_eta_cau):
            tokens = r.next_tokens()
            n_apert = parse_int(tokens[2])
            stages.append(
                {
                    "num_eta": parse_int(tokens[1]),
                    "apertures": [parse_int(t) for t in tokens[3 : 3 + n_apert]],
                }
            )
        simulations.append(stages)
    return {"n_simul": n_simul, "n_eta_cau": n_eta_cau, "simulations": simulations}


def parse_plpidap2(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_eta_cau = parse_int(r.next_tokens()[0])
    r.skip(1)
    stages = []
    for _ in range(n_eta_cau):
        tokens = r.next_tokens()
        n_apert = parse_int(tokens[2])
        stages.append(
            {"num_eta": parse_int(tokens[1]), "apertures": [parse_int(t) for t in tokens[3 : 3 + n_apert]]}
        )
    return {"n_eta_cau": n_eta_cau, "stages": stages}


# ---------------------------------------------------------------------------------------------
# Phase 2 file parsers
# ---------------------------------------------------------------------------------------------


def parse_plpcenre(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_cen = parse_int(r.next_tokens()[0])
    reservoirs = []
    for _ in range(n_cen):
        r.skip(1)
        plant_name = parse_name(r.next_tokens()[0])
        r.skip(1)
        reservoir_name = parse_name(r.next_tokens()[0])
        r.skip(1)
        rend_prom = parse_float(r.next_tokens()[0])
        r.skip(1)
        n_tramo = parse_int(r.next_tokens()[0])
        r.skip(1)
        segments = []
        for _ in range(n_tramo):
            ind, vol, pend, const, fesc = r.next_tokens()
            segments.append(
                {
                    "ind": parse_int(ind),
                    "volume": parse_float(vol),
                    "slope": parse_float(pend),
                    "constant": parse_float(const),
                    "scale": parse_float(fesc),
                }
            )
        reservoirs.append(
            {
                "plant_name": plant_name,
                "reservoir_name": reservoir_name,
                "avg_yield": rend_prom,
                "segments": segments,
            }
        )
    return {"n_cen": n_cen, "reservoirs": reservoirs}


def parse_plpcenpmax(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_cen = parse_int(r.next_tokens()[0])
    reservoirs = []
    for _ in range(n_cen):
        r.skip(1)
        plant_name = parse_name(r.next_tokens()[0])
        r.skip(1)
        reservoir_name = parse_name(r.next_tokens()[0])
        r.skip(1)
        n_tramo = parse_int(r.next_tokens()[0])
        r.skip(1)
        segments = []
        for _ in range(n_tramo):
            vol, pend, const = r.next_tokens()
            segments.append(
                {"volume": parse_float(vol), "slope": parse_float(pend), "constant": parse_float(const)}
            )
        reservoirs.append(
            {"plant_name": plant_name, "reservoir_name": reservoir_name, "segments": segments}
        )
    return {"n_cen": n_cen, "reservoirs": reservoirs}


def parse_plpcenbat(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_bat, max_iny = r.next_tokens()[:2]
    r.skip(1)
    batteries = []
    for _ in range(parse_int(n_bat)):
        bat_ind, bat_nom = r.next_tokens()[:2]
        r.skip(1)
        n_iny = parse_int(r.next_tokens()[0])
        injectors = []
        for _ in range(n_iny):
            r.skip(1)
            nom_iny, fpc = r.next_tokens()[:2]
            injectors.append({"name": parse_name(nom_iny), "loss_factor": parse_float(fpc)})
        r.skip(1)
        bar, fpd, emin, emax = r.next_tokens()[:4]
        batteries.append(
            {
                "ind": parse_int(bat_ind),
                "name": parse_name(bat_nom),
                "injectors": injectors,
                "bus": parse_int(bar),
                "discharge_loss_factor": parse_float(fpd),
                "capacity_min": parse_float(emin),
                "capacity_max": parse_float(emax),
            }
        )
    return {"n_bat": parse_int(n_bat), "max_iny": parse_int(max_iny), "batteries": batteries}


def _parse_plpcnfce_record(r: "RecordReader", *, has_estoc_findep: bool, has_vert: bool, econ_len: int) -> dict:
    """One plant record of plpcnfce.dat. Shape varies by block — see module map in
    static_formats.md#plpcnfce.dat and the cross-read of leecnfce.f in the Phase 2 plan notes."""
    r.skip(1)
    t1 = r.next_tokens()
    rec = {
        "cen_ind": parse_int(t1[0]),
        "name": parse_name(t1[1]),
        "cen_ipot": parse_int(t1[2]),
        "min_tec": parse_bool(t1[3]),
        "inter": parse_bool(t1[4]),
        "fcad": parse_bool(t1[5]),
        "mttd_hrz": parse_bool(t1[6]),
        "estoc_findep": parse_bool(t1[7]) if has_estoc_findep else None,
    }
    r.skip(1)
    t2 = r.next_tokens()
    rec["pot_min"] = parse_float(t2[0])
    rec["pot_max"] = parse_float(t2[1])
    rec["vert_min"] = parse_float(t2[2]) if has_vert else None
    rec["vert_max"] = parse_float(t2[3]) if has_vert else None
    r.skip(1)
    t3 = r.next_tokens()
    rec["cost_arranque"] = parse_float(t3[0])
    rec["cost_detencion"] = parse_float(t3[1])
    rec["on_flag"] = parse_bool(t3[2])
    r.skip(1)
    t4 = r.next_tokens()
    rec["cos_var"] = parse_float(t4[0])
    rec["rendimiento"] = parse_float(t4[1])
    rec["gen_bar"] = parse_int(t4[2])
    rec["gen_hid"] = parse_int(t4[3])
    rec["vert_hid"] = parse_int(t4[4])
    rec["p_ini"] = parse_float(t4[5])
    if econ_len >= 7:
        rec["cau_afl"] = parse_float(t4[6])
    else:
        rec["cau_afl"] = None
    if econ_len >= 13:
        rec["vol_ini"] = parse_float(t4[7])
        rec["vol_fin"] = parse_float(t4[8])
        rec["vol_min"] = parse_float(t4[9])
        rec["vol_max"] = parse_float(t4[10])
        rec["f_esc"] = parse_float(t4[11])
        rec["cfue"] = parse_bool(t4[12])
    return rec


def parse_plpcnfce(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    n_central, n_emb, n_ser, n_falla, n_pas, n_bat = (parse_int(t) for t in r.next_tokens()[:6])
    n_ter = n_central - n_emb - n_ser - n_pas - n_falla - n_bat
    r.skip(1)
    ft = r.next_tokens()
    header_flags = {
        "inter": parse_bool(ft[0]),
        "min_tec": parse_bool(ft[1]),
        "cad": parse_bool(ft[2]),
        "fase_sin_mt": parse_bool(ft[3]),
        "eta_ini_sin_mt": parse_int(ft[4]),
    }

    plants = []
    r.skip(2)
    for _ in range(n_emb):
        rec = _parse_plpcnfce_record(r, has_estoc_findep=True, has_vert=True, econ_len=13)
        rec["block"] = "EMBALSE"
        plants.append(rec)

    r.skip(1)
    for _ in range(n_ser):
        rec = _parse_plpcnfce_record(r, has_estoc_findep=True, has_vert=True, econ_len=7)
        rec["block"] = "SERIE"
        plants.append(rec)

    r.skip(1)
    for _ in range(n_pas):
        rec = _parse_plpcnfce_record(r, has_estoc_findep=True, has_vert=False, econ_len=7)
        rec["block"] = "PASADA"
        plants.append(rec)

    r.skip(1)
    for _ in range(n_ter):
        rec = _parse_plpcnfce_record(r, has_estoc_findep=False, has_vert=False, econ_len=6)
        rec["block"] = "TERMICA"
        plants.append(rec)

    r.skip(1)
    for i in range(n_bat + n_falla):
        rec = _parse_plpcnfce_record(r, has_estoc_findep=False, has_vert=False, econ_len=6)
        rec["block"] = "BATERIA" if i < n_bat else "FALLA"
        plants.append(rec)

    return {
        "n_central": n_central,
        "n_emb": n_emb,
        "n_ser": n_ser,
        "n_pas": n_pas,
        "n_falla": n_falla,
        "n_bat": n_bat,
        "n_ter": n_ter,
        "header_flags": header_flags,
        "plants": plants,
    }


def parse_plprun(text: str) -> dict:
    r = RecordReader.from_text(text)
    r.skip(2)
    plane_file = parse_name(r.next_tokens()[0])
    r.skip(1)
    iter_beg, iter_end = r.next_tokens()[:2]
    r.skip(1)
    open_mode = r.next_tokens()[0]
    return {
        "plane_file": plane_file,
        "iter_beg": parse_int(iter_beg),
        "iter_end": parse_int(iter_end),
        "open_mode": parse_int(open_mode),
    }
