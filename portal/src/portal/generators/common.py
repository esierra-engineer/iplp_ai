"""Shared helpers for every ``.dat`` generator.

Per the spec research (see plan): every PLP ``.dat`` reader uses Fortran list-directed READ, so
alignment/padding is cosmetic and comment-line *content* is never inspected — only the *count* of
header lines at each position matters. These helpers center the handful of format quirks so each
``generators/<file>.py`` module only supplies header text and field values, not manual line-counting
or ad-hoc formatting.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from io import StringIO


class DatWriter:
    """Accumulates lines for one .dat file. Use as a plain line-list builder — ``str(writer)``
    joins with '\\n' and a trailing newline, matching the sample files."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def comment(self, text: str) -> "DatWriter":
        """Emit one comment/header line. Content is free-form (never parsed by the solver) but by
        convention starts with '#' so the file reads the same way the originals did."""
        self._lines.append(text if text.startswith("#") else f"# {text}")
        return self

    def raw(self, line: str) -> "DatWriter":
        """Emit one data line verbatim (already formatted by the caller)."""
        self._lines.append(line)
        return self

    def fields(self, *values: object) -> "DatWriter":
        """Emit one data line from positional field values, whitespace-joined. Use `quote()`/
        `logical()` on individual values before passing them in where the spec requires quoting or
        T/F formatting."""
        self._lines.append(" ".join(str(v) for v in values))
        return self

    def blank_data_lines(self, count: int, values_per_line: Iterable[Iterable[object]]) -> "DatWriter":
        for values in values_per_line:
            self.fields(*values)
        return self

    def render(self) -> str:
        buf = StringIO()
        for line in self._lines:
            buf.write(line)
            buf.write("\n")
        return buf.getvalue()

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.render()


def quote(name: str) -> str:
    """Quote a name/string token, e.g. for bus/plant names: ``'AltoNorte110'``."""
    return f"'{name}'"


def logical(value: bool) -> str:
    """Fortran list-directed logical literal: bare T/F."""
    return "T" if value else "F"


def fiscal_month(calendar_month: int) -> int:
    """April-start fiscal month index (1=April..12=March), no year component. Several
    block-dependent files (plpdem.dat, plpcosce.dat, ...) carry a 'Mes' column in this convention
    — see db/models.py's Stage docstring for the full fiscal-calendar derivation (that one also
    needs a fiscal *year*; this file's callers only need the month, which needs no baseline)."""
    return calendar_month - 3 if calendar_month >= 4 else calendar_month + 9


def number(value: float, decimals: int = 6) -> str:
    """Fixed-decimal float formatting, rounding half-away-from-zero (like Excel/VBA's own
    formatting) rather than Python's f-string default of round-half-to-even on the binary float —
    the latter produces off-by-one-in-the-last-digit surprises exactly at values like 0.5445 that
    matter when comparing against VBA-authored golden files. Fortran list-directed READ accepts
    both 'e'/'E' and 'd'/'D' exponents and any amount of whitespace, so there is never a need to
    emit Fortran's own D-exponent notation — plain fixed-decimal formatting round-trips correctly."""
    quantum = Decimal(1).scaleb(-decimals)
    return str(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
