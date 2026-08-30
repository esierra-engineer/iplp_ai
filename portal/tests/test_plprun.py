from portal.generators import plprun

from .conftest import golden
from .parsers import parse_plprun


def test_plprun_matches_golden(session, case_id):
    generated = plprun.generate(session, case_id)
    assert parse_plprun(generated) == parse_plprun(golden("static", "plprun.dat"))
