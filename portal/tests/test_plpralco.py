from portal.generators import plpralco

from .conftest import golden
from .parsers import parse_plpralco


def test_plpralco_matches_golden(session, case_id):
    generated = plpralco.generate(session, case_id)
    assert parse_plpralco(generated) == parse_plpralco(golden("static", "plpralco.dat"))
