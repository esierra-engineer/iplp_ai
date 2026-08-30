from portal.generators import plplajam

from .conftest import golden
from .parsers import parse_lines_raw


def test_plplajam_matches_golden(session, case_id):
    generated = plplajam.generate(session, case_id)
    assert parse_lines_raw(generated) == parse_lines_raw(golden("static", "plplajam.dat"))
