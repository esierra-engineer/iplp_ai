from portal.generators import plpaflce

from .conftest import golden
from .parsers import parse_plpaflce


def test_plpaflce_matches_golden(session, case_id):
    generated = plpaflce.generate(session, case_id)
    got = parse_plpaflce(generated)
    want = parse_plpaflce(golden("block_dependant", "plpaflce.dat"))
    assert got["n_clase"] == want["n_clase"]
    got_by_name = {p["name"]: p for p in got["plants"]}
    want_by_name = {p["name"]: p for p in want["plants"]}
    # golden includes 2 plants ('ALTOPOLC', 'Sum_Isla_Mina') classified 'X' (fuera de servicio) in
    # the current Centrales sheet — excluded from `plant` entirely, same convention as
    # plpcnfce.dat's own plant count (see db/migrate_from_xlsm.py's _CENTRALES_TYPE_MAP). Their
    # historical inflow series simply isn't imported since there's no active Plant to attach it to.
    want_active = {n: p for n, p in want_by_name.items() if n not in ("ALTOPOLC", "Sum_Isla_Mina")}
    assert got["n_cen"] == len(want_active)
    assert set(got_by_name) == set(want_active)
    for name in want_active:
        assert got_by_name[name] == want_active[name], f"plant {name!r} differs"
