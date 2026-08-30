from portal.generators import plpdeb

from .conftest import golden
from .parsers import parse_plpdeb


def test_plpdeb_matches_golden(session, case_id):
    generated = plpdeb.generate(session, case_id)
    assert parse_plpdeb(generated) == parse_plpdeb(golden("static", "plpdeb.dat"))
