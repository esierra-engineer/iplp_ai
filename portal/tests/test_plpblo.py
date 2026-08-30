from portal.generators import plpblo

from .conftest import golden
from .parsers import parse_plpblo


def test_plpblo_matches_golden(session, case_id):
    generated = plpblo.generate(session, case_id)
    got = parse_plpblo(generated)
    want = parse_plpblo(golden("block_dependant", "plpblo.dat"))
    assert got == want
