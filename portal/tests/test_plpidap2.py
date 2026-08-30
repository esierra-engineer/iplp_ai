from portal.generators import plpidap2

from .conftest import golden
from .parsers import parse_plpidap2


def test_plpidap2_matches_golden(session, case_id):
    generated = plpidap2.generate(session, case_id)
    got = parse_plpidap2(generated)
    want = parse_plpidap2(golden("block_dependant", "plpidap2.dat"))
    assert got["n_eta_cau"] == want["n_eta_cau"]
    got_by_eta = {s["num_eta"]: s for s in got["stages"]}
    want_by_eta = {s["num_eta"]: s for s in want["stages"]}
    assert got_by_eta == want_by_eta
