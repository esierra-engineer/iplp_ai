from portal.generators import plpcnfli

from .conftest import golden
from .parsers import parse_plpcnfli


def test_plpcnfli_matches_golden(session, case_id):
    generated = plpcnfli.generate(session, case_id)
    got = parse_plpcnfli(generated)
    want = parse_plpcnfli(golden("static", "plpcnfli.dat"))
    # is_hvdc is intentionally not emitted (see generator docstring) — drop it from the golden
    # comparison too rather than requiring the generator to fabricate a matching value.
    for rec in want["lines"]:
        rec.pop("is_hvdc", None)
    assert got == want
