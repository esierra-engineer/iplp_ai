from portal.generators import plpmat

from .conftest import golden
from .parsers import parse_plpmat


def test_plpmat_matches_golden(session, case_id):
    generated = plpmat.generate(session, case_id)
    assert parse_plpmat(generated) == parse_plpmat(golden("static", "plpmat.dat"))
