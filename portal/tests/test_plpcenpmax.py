from portal.generators import plpcenpmax

from .conftest import golden
from .parsers import parse_plpcenpmax


def test_plpcenpmax_matches_golden(session, case_id):
    generated = plpcenpmax.generate(session, case_id)
    assert parse_plpcenpmax(generated) == parse_plpcenpmax(golden("static", "plpcenpmax.dat"))
