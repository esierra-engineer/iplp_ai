"""Spot-checks for the ported Vol_<Name> curves against fixed points visible directly in the VBA
source (branch boundaries, breakpoint-table endpoints) — not a re-derivation, just confirms the
transliteration didn't introduce an off-by-one or sign error."""

import pytest

from portal.curves.reservoir_volume import (
    volume_from_level,
    vol_colbun,
    vol_eltoro,
    vol_ralco,
)


def test_colbun_low_plateau():
    assert vol_colbun(390.0) == 319.1  # below the 393 cutoff, VBA returns the flat 319.1 constant


def test_colbun_piecewise_boundary():
    # VBA's Cotas/volumenes breakpoint table, i=1 segment
    assert vol_colbun(393.0) == pytest.approx(319.1, abs=1e-6)


def test_eltoro_breakpoint_table_ends():
    assert vol_eltoro(1300.0) == pytest.approx(0.0, abs=1e-6)
    assert vol_eltoro(1370.0) == pytest.approx(5826.53656, abs=1e-6)
    assert vol_eltoro(1400.0) == pytest.approx(5826.53656, abs=1e-6)  # clamped past the table


def test_ralco_breakpoint_table_ends():
    assert vol_ralco(598.0) == pytest.approx(0.0, abs=1e-6)
    assert vol_ralco(638.0) == pytest.approx(27.732006, abs=1e-6)


def test_dispatch_by_name_is_case_insensitive():
    assert volume_from_level("ralco", 598.0) == volume_from_level("RALCO", 598.0)


def test_unknown_reservoir_raises():
    with pytest.raises(KeyError):
        volume_from_level("NOT_A_RESERVOIR", 100.0)
