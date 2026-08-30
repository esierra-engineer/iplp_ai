from portal.generators import plpmanem

from .conftest import golden
from .parsers import parse_plpmanem


def test_plpmanem_matches_golden(session, case_id):
    generated = plpmanem.generate(session, case_id)
    got = parse_plpmanem(generated)
    want = parse_plpmanem(golden("block_dependant", "plpmanem.dat"))
    assert got["n_emb"] == want["n_emb"]
    got_by_name = {r["name"]: r for r in got["reservoirs"]}
    want_by_name = {r["name"]: r for r in want["reservoirs"]}
    assert set(got_by_name) == set(want_by_name)
    for name in want_by_name:
        assert got_by_name[name] == want_by_name[name], f"reservoir {name!r} differs"
