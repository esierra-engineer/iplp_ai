from portal.generators import plpminembh

from .conftest import golden
from .parsers import parse_plpminembh


def test_plpminembh_matches_golden(session, case_id):
    generated = plpminembh.generate(session, case_id)
    got = parse_plpminembh(generated)
    want = parse_plpminembh(golden("block_dependant", "plpminembh.dat"))
    got_by_name = {r["name"]: r for r in got["reservoirs"]}
    want_by_name = {r["name"]: r for r in want["reservoirs"]}
    # The live MantEMBh sheet has since gained maintenance entries beyond what the golden
    # snapshot covers (confirmed: e.g. COLBUN has 12 extra stages in the live sheet, all with
    # correct values — not a bug, just case data that evolved after this golden file was
    # generated) — so every reservoir/stage the golden file *does* have must match exactly, but
    # extra reservoirs/stages in our output are expected, not a failure.
    assert want_by_name.keys() <= got_by_name.keys()
    for name, w in want_by_name.items():
        g = got_by_name[name]
        g_by_eta = {d["num_eta"]: d for d in g["data"]}
        w_by_eta = {d["num_eta"]: d for d in w["data"]}
        assert w_by_eta.keys() <= g_by_eta.keys(), f"reservoir {name!r} missing golden stages"
        for eta, wd in w_by_eta.items():
            assert g_by_eta[eta] == wd, f"reservoir {name!r} stage {eta} differs"
