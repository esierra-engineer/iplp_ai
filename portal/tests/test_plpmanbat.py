from portal.generators import plpmanbat

from .conftest import golden
from .parsers import parse_plpmanbat


def test_plpmanbat_matches_golden(session, case_id):
    generated = plpmanbat.generate(session, case_id)
    got = parse_plpmanbat(generated)
    # Golden reference is the checked-in plpmantbat.dat (mismatched filename in this repo's
    # solver checkout — see the user's 2026-08-30 ruling in db/models.py/README.md); the generator
    # itself writes plpmanbat.dat.
    want = parse_plpmanbat(golden("block_dependant", "plpmantbat.dat"))
    assert got["n_bat"] == want["n_bat"]
    got_by_name = {b["name"]: b for b in got["batteries"]}
    want_by_name = {b["name"]: b for b in want["batteries"]}
    assert set(got_by_name) == set(want_by_name)
    for name in want_by_name:
        assert got_by_name[name] == want_by_name[name], f"battery {name!r} differs"
