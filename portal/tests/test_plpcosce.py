from portal.generators import plpcosce

from .conftest import golden
from .parsers import parse_plpcosce


def test_plpcosce_matches_golden(session, case_id):
    generated = plpcosce.generate(session, case_id)
    got = parse_plpcosce(generated)
    want = parse_plpcosce(golden("block_dependant", "plpcosce.dat"))
    assert got["n_cen"] == want["n_cen"]
    got_by_name = {p["name"]: p for p in got["plants"]}
    want_by_name = {p["name"]: p for p in want["plants"]}
    assert set(got_by_name) == set(want_by_name)
    for name in want_by_name:
        assert got_by_name[name] == want_by_name[name], f"plant {name!r} differs"
