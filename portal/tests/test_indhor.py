from portal.generators import indhor

from .conftest import golden
from .parsers import parse_indhor_csv


def test_indhor_matches_golden(session, case_id):
    generated = indhor.generate(session, case_id)
    got = parse_indhor_csv(generated)
    want = parse_indhor_csv(golden("block_dependant", "indhor.csv"))
    assert len(got) == len(want)
    for i, (g, w) in enumerate(zip(got, want)):
        assert g == w, f"row {i} differs: {g} vs {w}"
