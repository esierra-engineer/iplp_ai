# PLP Case Portal

SQLite + Python + web replacement for the Excel/VBA pipeline in `../xlsm` and `../xla` that
authors PLP model case data and generates the `.dat` files the PLP solver reads. See
`/home/erick/.claude/plans/ethereal-scribbling-tiger.md` for the full phased plan; this covers
what's implemented so far.

## Status: Phase 0 + 1 + 2 complete

- **Phase 0** — `curves/reservoir_volume.py`: the 15 `Vol_<Name>` reservoir level→volume rating
  curves ported from `xla/FUNCCDEC_CDEC.xla`, needed by Phase 4's maintenance generators.
- **Phase 1** — calendar & topology: `stage`/`block`/`bus`/`line` tables, generators for
  `plpbar.dat`, `plpeta.dat`, `plpblo.dat`, `plpcnfli.dat`, `plpmat.dat`, `plpdeb.dat`,
  `plprun.dat`, a migration importer from the live `.xlsm`, and a FastAPI + htmx web UI (buses,
  lines, stages, and a "generate .dat files" page).
- **Phase 2** — plant fleet: `plant` (+ `reservoir`, `reservoir_yield_curve`,
  `reservoir_pmax_curve`, `battery` tables), generators for `plpcnfce.dat` (2,964 plants across 6
  type-blocks — the largest/most structurally complex file in the whole project),
  `plpcenre.dat`, `plpcenpmax.dat`, `plpcenbat.dat`; a migration importer from the Centrales/
  Baterias sheets (column mapping empirically validated against the golden file's real values, not
  just the sheet's header labels); paginated/filterable Plants and Batteries web UI pages.

  Two files — `plpcenre.dat` and `plpcenpmax.dat` — have **no VBA writer at all** in either `.xla`
  workbook (searched both); their reservoir rating-curve data is bootstrapped straight from the
  golden files, same mechanism as Phase 1's undetermined fields. Same for `plpcnfce.dat`'s
  per-embalse `EmbFEsc` scale factor.

## Setup

```
uv sync --group dev
```

## Import a case

```
uv run python -m portal import-xlsm \
  --name "IPLP20251001_c00" \
  --xlsm ../xlsm/IPLP20251001_c00.xlsm \
  --dat-static ../dat/static \
  --dat-block-dependant ../dat/block_dependant
```

Writes to `portal.sqlite3` at the project root (override with `PORTAL_DB_PATH`).

## Run the web app

```
uv run uvicorn portal.web.app:app --reload
```

Then open `http://127.0.0.1:8000/cases`.

## Run the tests

```
uv run pytest
```

Each `test_<file>.py` seeds an in-memory case from the live `.xlsm` (+ the current golden `.dat`
files for fields not yet derivable from Excel — see below), regenerates the file, and compares it
against the corresponding golden file in `tests/golden/` using the permissive record-structure
parsers in `tests/parsers.py` (field-value equality, not byte-for-byte diff — matching how the
Fortran solver itself reads these files: list-directed, comment lines ignored by position only).

## Known bootstrap limitations (tracked, not hidden)

A few fields are seeded straight from the case's *existing* golden `.dat` files rather than derived
from the `.xlsm`, because the derivation logic is out of scope so far, or (for two files) because
no Excel/VBA source exists at all — see `db/migrate_from_xlsm.py`'s module docstring for the full
list and why. In short: `Stage.hydro_dependent`/`Stage.rate_factor`, all `Block` durations, the
three solver-control files' values, `Reservoir.f_esc`, and all of `plpcenre.dat`/`plpcenpmax.dat`.
A from-scratch case with no pre-existing `.dat` files will need those derivations ported first
(for `plpcenre.dat`/`plpcenpmax.dat`, "ported" means "sourced from wherever this data is actually
maintained" — there's no VBA logic to port, since none was ever there).

Per the user's decision (2026-08-30): where this repo's `plp_cen` checkout of the solver disagrees
with a checked-in sample filename, **the code is the rule** — the sample's name is taken as the
error. This resolved the `plpmanbat.dat` (code) vs `plpmantbat.dat` (sample) mismatch flagged
after Phase 1: Phase 4's battery-maintenance generator should write `plpmanbat.dat`.
