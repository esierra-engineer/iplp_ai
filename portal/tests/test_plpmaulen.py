from portal.generators import plpmaulen

from .conftest import golden
from .parsers import parse_lines_raw


def test_plpmaulen_matches_golden(session, case_id):
    generated = plpmaulen.generate(session, case_id)
    assert parse_lines_raw(generated) == parse_lines_raw(golden("static", "plpmaulen.dat"))
