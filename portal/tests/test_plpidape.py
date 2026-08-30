from portal.generators import plpidape

from .conftest import golden
from .parsers import parse_plpidape


def test_plpidape_matches_golden(session, case_id):
    generated = plpidape.generate(session, case_id)
    got = parse_plpidape(generated)
    want = parse_plpidape(golden("block_dependant", "plpidape.dat"))
    assert got["n_simul"] == want["n_simul"]
    assert got["n_eta_cau"] == want["n_eta_cau"]
    for got_sim, want_sim in zip(got["simulations"], want["simulations"]):
        got_by_eta = {s["num_eta"]: s for s in got_sim}
        want_by_eta = {s["num_eta"]: s for s in want_sim}
        assert got_by_eta == want_by_eta
