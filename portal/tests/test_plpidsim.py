from portal.generators import plpidsim

from .conftest import golden
from .parsers import parse_plpidsim


def test_plpidsim_matches_golden(session, case_id):
    generated = plpidsim.generate(session, case_id)
    got = parse_plpidsim(generated)
    want = parse_plpidsim(golden("block_dependant", "plpidsim.dat"))
    assert got["n_simul"] == want["n_simul"]
    assert got["n_eta_cau"] == want["n_eta_cau"]
    got_by_eta = {s["num_eta"]: s for s in got["stages"]}
    want_by_eta = {s["num_eta"]: s for s in want["stages"]}
    assert got_by_eta == want_by_eta
