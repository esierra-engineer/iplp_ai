from portal.generators import plpfilemb

from .conftest import golden
from .parsers import parse_plpfilemb


def test_plpfilemb_matches_golden(session, case_id):
    generated = plpfilemb.generate(session, case_id)
    got = parse_plpfilemb(generated)
    want = parse_plpfilemb(golden("static", "plpfilemb.dat"))
    assert got["n_cen"] == want["n_cen"]
    got_by_name = {r["name"]: r for r in got["reservoirs"]}
    want_by_name = {r["name"]: r for r in want["reservoirs"]}
    assert got_by_name == want_by_name
