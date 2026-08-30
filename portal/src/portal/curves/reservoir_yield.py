"""Per-reservoir level ('Cota', m.s.n.m.) -> average yield ('Rendimiento', MWh/m3/s) curves.

Same situation and same source as reservoir_volume.py's `Vol_<Name>` curves: ported from
`xla/FUNCCDEC_CDEC.xla`'s `Rend_<Name>` VBA functions, line-for-line, not re-fit. Used the same way
— recovering a Centrales-sheet `Rendimiento` cell when it's cached as an Excel formula error
(`#NAME?`) because the FUNCCDEC_CDEC.xla add-in wasn't loaded at recalc time (confirmed to happen
in real, currently-used workbooks — see db/migrate_from_xlsm.py).

Only the reservoirs FUNCCDEC_CDEC.xla actually defines a `Rend_<Name>` for are covered here — not
every reservoir with a `Vol_<Name>` curve has one (e.g. LMAULE is a pure storage/aux embalse with
no direct turbine, so it has no rendimiento formula at all in the source workbook either).
"""

from __future__ import annotations


def rend_colbun(cota: float) -> float:
    """VBA: COLBUN.Rend_COLBUN."""
    rend0, cota0, cotad = 1.55, 430.55, 267.76
    return rend0 * (cota - cotad) / (cota0 - cotad)


def rend_eltoro(cota: float) -> float:
    """VBA: ELTORO.Rend_ELTORO."""
    cons1, cons2 = 0.008, 5.931
    return cons1 * cota - cons2


def rend_canutillar(cota: float) -> float:
    """VBA: CANUTILLAR.Rend_CANUTILLAR."""
    rend0, cons1, cons2, cons3 = 2.082606, -0.018920591, 0.000120086, -0.0000001742
    return rend0 + cota * cons1 + cota**2 * cons2 + cota**3 * cons3


def rend_cipreses(cota: float) -> float:
    """VBA: CIPRESES.Rend_CIPRESES."""
    cons1, cons2, cons3 = -354.62162659, 0.5410166883, -0.0002046658
    return cons1 + cons2 * cota + cons3 * cota**2


def rend_pehuenche(cota: float) -> float:
    """VBA: PEHUENCHE.Rend_PEHUENCHE."""
    d0, d1, d2 = 17.2105, -0.0563686, 0.0000502872
    return d0 + d1 * cota + d2 * cota * cota


def rend_rapel(cota: float) -> float:
    """VBA: RAPEL.Rend_RAPEL."""
    cons1, cons2, cons3 = -1.18346, 0.026904, -0.00009
    return cons1 + cons2 * cota + cons3 * cota**2


def rend_ralco(cota: float) -> float:
    """VBA: RALCO.Rend_RALCO."""
    pend, cte0 = 0.0089, -4.721475
    return pend * cota + cte0


def rend_pangue(cota: float) -> float:
    """VBA: PANGUE.Rend_PANGUE."""
    cons1, cons2, cons3 = -3.6981, 0.0094, -0.0000008
    return cons1 + cons2 * cota + cons3 * cota**2


RESERVOIR_YIELD_CURVES = {
    "COLBUN": rend_colbun,
    "ELTORO": rend_eltoro,
    "CANUTILLAR": rend_canutillar,
    "CIPRESES": rend_cipreses,
    "PEHUENCHE": rend_pehuenche,
    "RAPEL": rend_rapel,
    "RALCO": rend_ralco,
    "PANGUE": rend_pangue,
}


def yield_from_level(reservoir_name: str, cota: float) -> float:
    """Level (m.s.n.m.) -> average yield (MWh/m3/s) for the named reservoir.

    Raises KeyError if the reservoir has no ported yield curve (either it genuinely has none in
    FUNCCDEC_CDEC.xla, like LMAULE, or one hasn't been added here yet) — callers should surface
    that as a clear error rather than silently defaulting.
    """
    try:
        fn = RESERVOIR_YIELD_CURVES[reservoir_name.upper()]
    except KeyError as exc:
        raise KeyError(
            f"No ported Rend_{reservoir_name.upper()} yield curve — add one to "
            "reservoir_yield.py before relying on this reservoir's recovered rendimiento."
        ) from exc
    return fn(cota)
