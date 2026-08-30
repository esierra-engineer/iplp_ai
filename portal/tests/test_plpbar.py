from portal.generators import plpbar

from .conftest import golden
from .parsers import parse_plpbar


def test_plpbar_matches_golden(session, case_id):
    generated = plpbar.generate(session, case_id)
    got = parse_plpbar(generated)
    want = parse_plpbar(golden("static", "plpbar.dat"))
    assert got == want
