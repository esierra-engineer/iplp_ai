from portal.generators import plpextrac

from .conftest import golden
from .parsers import parse_plpextrac


def test_plpextrac_matches_golden(session, case_id):
    generated = plpextrac.generate(session, case_id)
    got = parse_plpextrac(generated)
    want = parse_plpextrac(golden("static", "plpextrac.dat"))
    assert got["n_cen"] == want["n_cen"]
    assert sorted(got["points"], key=str) == sorted(want["points"], key=str)
