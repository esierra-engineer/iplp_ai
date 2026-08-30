from portal.generators import plpcenre

from .conftest import golden
from .parsers import parse_plpcenre


def test_plpcenre_matches_golden(session, case_id):
    generated = plpcenre.generate(session, case_id)
    assert parse_plpcenre(generated) == parse_plpcenre(golden("static", "plpcenre.dat"))
