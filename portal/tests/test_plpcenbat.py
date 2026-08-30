from portal.generators import plpcenbat

from .conftest import golden
from .parsers import parse_plpcenbat


def test_plpcenbat_matches_golden(session, case_id):
    generated = plpcenbat.generate(session, case_id)
    assert parse_plpcenbat(generated) == parse_plpcenbat(golden("static", "plpcenbat.dat"))
