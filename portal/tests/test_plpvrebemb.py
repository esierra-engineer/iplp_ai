from portal.generators import plpvrebemb

from .conftest import golden
from .parsers import parse_plpvrebemb


def test_plpvrebemb_matches_golden(session, case_id):
    generated = plpvrebemb.generate(session, case_id)
    got = parse_plpvrebemb(generated)
    want = parse_plpvrebemb(golden("static", "plpvrebemb.dat"))
    assert got["n_emb"] == want["n_emb"]
    got_by_name = {r["name"]: r for r in got["reservoirs"]}
    want_by_name = {r["name"]: r for r in want["reservoirs"]}
    assert got_by_name == want_by_name
