"""Per-reservoir level ('Cota', m.s.n.m.) -> volume (Hm3) rating curves.

Ported directly from the ``Vol_<Name>`` VBA functions in ``xla/FUNCCDEC_CDEC.xla``. Those functions
are what ``Archivo_11`` (the ``plpmanem.dat`` / reservoir-maintenance VBA writer) calls at runtime via
``Application.Run("Vol_" & ReservoirName, level)`` to convert a maintenance sheet's level entry into
the volume value the .dat file actually stores — see Phase 4 of the plan.

Each function below is a line-for-line translation of its VBA counterpart (same branches, same
literal coefficients), not a re-fit — this file is data/logic ported for parity, not a new model.
Only the ``Vol_*`` direction is ported (level -> volume); the inverse ``Cot_*`` (volume -> level)
functions are not needed by anything in this plan's scope and are intentionally left out.

VBA source module per function (all in ``xla/FUNCCDEC_CDEC.xla``): COLBUN, ELTORO, CANUTILLAR,
CIPRESES, POLCURA, LMAULE, PEHUENCHE, RAPEL, MACHICURA, PANGUE, RALCO, ANGOSTURA, PILMAIQUEN,
RUCATAYO, PULLINQUE.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------------------------
# Shared VBA `punteroX` bisection helper (right-endpoint binary search over an ascending array,
# 1-based in the original VBA). Every reservoir module below that needs breakpoint-table lookup
# (COLBUN's low-level segment, ELTORO, RALCO) uses the same algorithm; VBA duplicated it per
# module (punteroA/punteroB/punteroC) with hardcoded module-level arrays — here it's one function.
# ---------------------------------------------------------------------------------------------


def _bisect_right_index(values: list[float], x: float) -> int:
    """Return the 1-based index i (VBA convention) such that ``values[i-1]`` is the right endpoint
    bracketing x in the ascending ``values`` array, matching VBA's punteroA/B/C exactly."""
    j, k = 1, len(values)
    while (k - j) > 1:
        i = (k + j) // 2  # VBA RoundDown((k+j)/2, 0) == floor for positive operands
        if x <= values[i - 1]:
            k = i
        else:
            j = i
    return k


def vol_colbun(cota: float) -> float:
    """VBA: COLBUN.Vol_COLBUN."""
    a3, a2, a1, a0 = 215.679132, -564.993651, 496.907289, -146.591083
    cmax, vmax = 437.0, 1550.63
    if cota < 393.0:
        return 319.1
    if cota < 397.0:
        cotas = [393.0, 394.0, 395.0, 396.0, 397.0]
        vols = [319.1, 333.76, 348.83, 364.32, 380.22]
        i = math.floor(cota - 392.0)  # 1-based VBA index, in [1, 4] on this branch
        m = vols[i] - vols[i - 1]
        b = vols[i - 1] - cotas[i - 1] * m
        return m * cota + b
    x = cota / cmax
    return (a1 * x + a2 * x**2 + a3 * x**3 + a0) * vmax


# ELTORO's Vol_ELTORO: Datos(1..71), one value per integer step of (Cota - 1300), from the VBA
# source verbatim (Volumen [mill m3] del Lago Laja en función de la Cota [m.s.n.m.]).
_ELTORO_DATOS = [
    0.0, 48.28954, 97.47766, 147.26746, 197.35679, 248.04517, 299.43508, 351.82341, 405.0131,
    459.20122, 514.48761, 570.97736, 628.56274, 687.35149, 747.53804, 808.92531, 871.61054,
    935.59635, 1000.88273, 1067.4697, 1135.25477, 1204.23795, 1274.32464, 1345.60945, 1417.89268,
    1491.07712, 1565.25999, 1640.4439, 1716.42655, 1793.41026, 1871.19533, 1949.97619, 2029.56105,
    2110.14171, 2191.52373, 2273.9068, 2357.18845, 2441.47116, 2526.65244, 2612.83215, 2700.01554,
    2788.19472, 2877.37496, 2967.75593, 3059.03548, 3151.31608, 3244.69758, 3339.17471, 3434.65552,
    3531.13476, 3628.71226, 3727.4905, 3827.36962, 3928.44686, 4030.62499, 4133.90402, 4238.58084,
    4344.35855, 4451.33437, 4559.61076, 4668.98805, 4779.66329, 4891.53927, 5004.41367, 5118.38896,
    5233.46515, 5349.83928, 5467.31431, 5585.88761, 5705.66164, 5826.53656,
]


def vol_eltoro(cota: float) -> float:
    """VBA: ELTORO.Vol_ELTORO."""
    if cota >= 1370.0:
        return _ELTORO_DATOS[-1]
    rel = cota - 1300.0
    i = min(math.floor(rel) + 2, 71)  # 1-based VBA index
    vol = _ELTORO_DATOS[i - 2] + (rel - math.floor(rel)) * (_ELTORO_DATOS[i - 1] - _ELTORO_DATOS[i - 2])
    return max(vol, 0.0)


def vol_canutillar(cota: float) -> float:
    """VBA: CANUTILLAR.Vol_CANUTILLAR."""
    if cota < 230.0:
        return 44.9739 * cota - 9894.258
    if cota <= 240.0:
        return 46.3472 * cota - 10210.117
    return 50.7225 * cota - 11260.189


def vol_cipreses(cota: float) -> float:
    """VBA: CIPRESES.Vol_CIPRESES."""
    if cota <= 1280.0:
        return 0.0
    a0, a1, a2 = 134744.88984, -211.91025423, 0.0833132678
    return a0 + a1 * cota + a2 * cota**2


def vol_polcura(cota: float) -> float:
    """VBA: POLCURA.Vol_POLCURA."""
    a0, a1, a2, a3, a4, a5 = (
        0.6976365827, 90.859293303, 40.08341237, -13.9725593488, 2.5864430194, -0.159930272,
    )
    dcota = cota - 730.0
    return (a0 + a1 * dcota + a2 * dcota**2 + a3 * dcota**3 + a4 * dcota**4 + a5 * dcota**5) / 1000.0


def vol_lmaule(cota: float) -> float:
    """VBA: LMAULE.Vol_LMAULE."""
    a0, a1, a2, a3, a4, a5 = (
        -0.426511610904754, 39.85091749344, 0.713891558517388,
        -2.68621789452889e-02, 7.69400535914122e-04, -8.51368088853222e-06,
    )
    dcota = cota - 2152.135
    vol = a0 + a1 * dcota + a2 * dcota**2 + a3 * dcota**3 + a4 * dcota**4 + a5 * dcota**5
    return max(vol, 0.0)


def vol_pehuenche(cota: float) -> float:
    """VBA: PEHUENCHE.Vol_PEHUENCHE."""
    a0, a1, a2 = 12532.0161, -42.383595, 0.0358801
    return a0 + a1 * cota + a2 * cota**2


def vol_rapel(cota: float) -> float:
    """VBA: RAPEL.Vol_RAPEL."""
    a0, a1, a2, a3 = -36039.35, 1279.686867, -15.1802416, 0.060121028
    vol = a0 + a1 * cota + a2 * cota**2 + a3 * cota**3
    return max(vol, 65.3)


def vol_machicura(cota: float) -> float:
    """VBA: MACHICURA.Vol_MACHICURA."""
    if cota < 254.5:
        return 0.0
    a0, a1, a2, a3, a4, a5 = 0.220082, 3.869693, 0.854351, -0.346473, 0.080443, -0.007131
    dcota = cota - 254.0
    return a0 + a1 * dcota + a2 * dcota**2 + a3 * dcota**3 + a4 * dcota**4 + a5 * dcota**5


def vol_pangue(cota: float) -> float:
    """VBA: PANGUE.Vol_PANGUE."""
    a0, a1, a2 = 7091.6, -32.43, 0.0366
    vol = 0.0 if cota < 493.0 else a0 + a1 * cota + a2 * cota**2
    return max(vol, 0.0)


_RALCO_COTAS = [598.0, 600.0, 610.0, 620.0, 630.0, 635.0, 636.0, 637.0, 638.0]
_RALCO_VOL_INF = [0.0, 0.02132, 0.43767, 4.90172, 15.43637, 22.730575, 24.318677, 25.984148, 27.732006]


def vol_ralco(cota: float) -> float:
    """VBA: RALCO.Vol_Ralco. Breakpoint table for Cota<=638, cubic polynomial above."""
    if cota <= _RALCO_COTAS[-1]:
        i = _bisect_right_index(_RALCO_COTAS, cota)  # 1-based
        return (
            (_RALCO_VOL_INF[i - 1] - _RALCO_VOL_INF[i - 2])
            / (_RALCO_COTAS[i - 1] - _RALCO_COTAS[i - 2])
        ) * (cota - _RALCO_COTAS[i - 1]) + _RALCO_VOL_INF[i - 1]
    a3, a2, a1, a0 = 0.9869, -72.676, 2789.6, -30351.0
    cota_r = cota - _RALCO_COTAS[0]
    return (a0 + a1 * cota_r + a2 * cota_r**2 + a3 * cota_r**3) / 1000.0


def vol_angostura(cota: float) -> float:
    """VBA: ANGOSTURA.Vol_ANGOSTURA."""
    if cota < 280.0:
        return 1.42084270641058e-02 * cota**2 - 7.55794967587359 * cota + 1005.0989369465
    if cota < 290.0:
        return 0.023812857004521 * cota**2 - 12.9330770375678 * cota + 1757.21857766058
    if cota < 296.0:
        return 5.76911113283868e-02 * cota**2 - 32.3727074657782 * cota + 4545.81085866535
    if cota < 302.0:
        return 0.107207786948566 * cota**2 - 61.5307295123461 * cota + 8838.26697394881
    if cota < 310.0:
        return 0.141958163277288 * cota**2 - 82.4673316143121 * cota + 11991.7130189995
    if cota < 316.0:
        return 0.112940353957764 * cota**2 - 64.5547375536446 * cota + 9227.31750858668
    return 0.172040377016484 * cota**2 - 102.168372622437 * cota + 15211.766064903


def vol_pilmaiquen(cota: float) -> float:
    """VBA: PILMAIQUEN.Vol_PILMAIQUEN."""
    a0, a1 = 102.0, 103.7
    c = min(cota, a1)
    return (c - a0) * 117 * 100 * 14148 / 1_000_000


def vol_rucatayo(cota: float) -> float:
    """VBA: RUCATAYO.Vol_RUCATAYO."""
    a0, a1 = 144.0, 148.0
    c = min(cota, a1)
    return ((c - a0) * 397552.5 + 4816560) / 1_000_000


def vol_pullinque(cota: float) -> float:
    """VBA: PULLINQUE.Vol_PULLINQUE."""
    a0, a1, a2 = 194.4, 195.64, 0.16574585635344
    c = max(min(cota, a1), a0)
    return (c - a0) / a2


# Registry keyed by reservoir name, uppercase, matching the "Vol_" & NombreE(IEmb) dispatch in
# Archivo_11. Extend this table if a future case introduces a reservoir not in the current fleet.
RESERVOIR_VOLUME_CURVES = {
    "COLBUN": vol_colbun,
    "ELTORO": vol_eltoro,
    "CANUTILLAR": vol_canutillar,
    "CIPRESES": vol_cipreses,
    "POLCURA": vol_polcura,
    "LMAULE": vol_lmaule,
    "PEHUENCHE": vol_pehuenche,
    "RAPEL": vol_rapel,
    "MACHICURA": vol_machicura,
    "PANGUE": vol_pangue,
    "RALCO": vol_ralco,
    "ANGOSTURA": vol_angostura,
    "PILMAIQUEN": vol_pilmaiquen,
    "RUCATAYO": vol_rucatayo,
    "PULLINQUE": vol_pullinque,
}


def volume_from_level(reservoir_name: str, cota: float) -> float:
    """Level (m.s.n.m.) -> volume (Hm3) for the named reservoir.

    Raises KeyError if the reservoir has no ported rating curve — callers (Phase 4's maintenance
    importer) should surface that as a clear "no curve for this reservoir" error rather than a
    silent default, mirroring the fact that VBA's ``Application.Run`` would itself fail loudly if
    the ``Vol_<Name>`` macro didn't exist.
    """
    try:
        fn = RESERVOIR_VOLUME_CURVES[reservoir_name.upper()]
    except KeyError as exc:
        raise KeyError(
            f"No ported Vol_{reservoir_name.upper()} rating curve — add one to "
            "reservoir_volume.py before importing maintenance data for this reservoir."
        ) from exc
    return fn(cota)
