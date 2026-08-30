from portal.generators import plpdem

from .conftest import golden
from .parsers import parse_plpdem


def test_plpdem_matches_golden(session, case_id):
    generated = plpdem.generate(session, case_id)
    got = parse_plpdem(generated)
    want = parse_plpdem(golden("block_dependant", "plpdem.dat"))
    assert got["n_bar"] == want["n_bar"]
    got_by_name = {b["name"]: b for b in got["buses"]}
    want_by_name = {b["name"]: b for b in want["buses"]}
    assert set(got_by_name) == set(want_by_name)
    for name in want_by_name:
        g, w = got_by_name[name], want_by_name[name]
        assert g["n_blo_dem"] == w["n_blo_dem"], f"bus {name!r} demand-row-count differs"
        for gd, wd in zip(g["data"], w["data"]):
            assert gd["num_blo"] == wd["num_blo"]
            # Exact to the file's own 2-decimal precision (verified: max diff across all 32,526
            # (bus, block) pairs in this case is 0.0) — a tiny epsilon only guards float noise.
            assert abs(gd["demanda"] - wd["demanda"]) < 1e-6, (
                f"bus {name!r} block {gd['num_blo']} demand differs: {gd['demanda']} vs {wd['demanda']}"
            )
