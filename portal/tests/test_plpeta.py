from portal.generators import plpeta

from .conftest import golden
from .parsers import parse_plpeta


def test_plpeta_matches_golden(session, case_id):
    generated = plpeta.generate(session, case_id)
    got = parse_plpeta(generated)
    want = parse_plpeta(golden("block_dependant", "plpeta.dat"))
    assert got == want
