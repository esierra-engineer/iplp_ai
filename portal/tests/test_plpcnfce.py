from portal.generators import plpcnfce

from .conftest import golden
from .parsers import parse_plpcnfce


def test_plpcnfce_matches_golden(session, case_id):
    generated = plpcnfce.generate(session, case_id)
    got = parse_plpcnfce(generated)
    want = parse_plpcnfce(golden("static", "plpcnfce.dat"))
    assert got["n_central"] == want["n_central"]
    assert got["n_emb"] == want["n_emb"]
    assert got["n_ser"] == want["n_ser"]
    assert got["n_pas"] == want["n_pas"]
    assert got["n_ter"] == want["n_ter"]
    assert got["n_bat"] == want["n_bat"]
    assert got["n_falla"] == want["n_falla"]
    assert got["header_flags"] == want["header_flags"]
    # Compare plant-by-plant so a mismatch reports which one, not a single huge list diff.
    assert len(got["plants"]) == len(want["plants"])
    for i, (g, w) in enumerate(zip(got["plants"], want["plants"])):
        assert g == w, f"plant #{i} ({g.get('name')!r} vs {w.get('name')!r}) differs"
