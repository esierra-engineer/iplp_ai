# PLP Case Portal

SQLite + Python + web replacement for the Excel/VBA pipeline in `../xlsm` and `../xla` that
authors PLP model case data and generates the `.dat` files the PLP solver reads. See
`/home/erick/.claude/plans/ethereal-scribbling-tiger.md` for the full phased plan; this covers
what's implemented so far.

## Status: All 7 phases complete

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
- **Phase 3** — demand & thermal costs: `demand_profile` (~480k rows: the Demanda-R/L/LD sheets'
  normalized hourly load shapes), `consumption_week`/`holiday` (Consumo sheet), `industrial_project`
  (Proyectos sheet), `thermal_cost_schedule` (CV_MP sheet); `demand_calc.py` — a full Python port
  of `Rutina04.DEMxBarra2` (per-bus demand disaggregation: normalized shape × weekly system-wide
  GWh target, plus industrial project overlay) and the block-aggregation loop in
  `Archivo_03_PLPDEM_5A` — feeding generators for `plpdem.dat`, `indhor.csv`, and `plpcosce.dat`.
  Industrial Projects and Thermal Cost Schedule web UI pages.

  This was a genuine algorithm port, not a bootstrap — and it reproduces the golden `plpdem.dat`
  and `plpcosce.dat` **exactly** (0.0 max difference across all 32,526 (bus, block) demand values
  in this case). Tracing it also surfaced that Archivo_03's non-"_5A"-suffixed module is dead code
  for this workbook (it references a `Demanda-I` sheet that doesn't exist) — the "_5A"-suffixed
  module is actually the one active module for every run mode, `CDECSimTyp` gating its internal
  behavior rather than the module choice itself gating on file/macro name as the suffix suggests.

  One correctness-affecting discovery while tracing this: block hour-counts for "mensual" mode are
  **not** a duration-curve computation — they're literal extra columns on the Etapas sheet (one per
  block), and a stage's blocks are calendar day-slices that repeat identically every day of that
  stage, not chronological chunks of the whole stage. `Stage.start_date` was added to the schema to
  support this — and Phase 1's Block import was later fixed to derive durations directly from those
  same Etapas-sheet columns (see "Importing from the .xlsm alone" below) instead of bootstrapping
  from the golden `plpblo.dat`.
- **Phase 4** — maintenance schedules: `plant_maintenance`, `line_maintenance`,
  `reservoir_maintenance`, `reservoir_min_volume_slack`, `battery_maintenance`; generators for
  `plpmance.dat` (2,783 plants, ~610k data rows — the largest golden file in the project at 36.7MB),
  `plpmanli.dat`, `plpmanem.dat`, `plpminembh.dat`, `plpmanbat.dat` (written under that name per the
  user's 2026-08-30 filename ruling, even though the checked-in sample is `plpmantbat.dat`).

  Three of these four Excel-sourced tables turned out to have a **pre-merged block/stage-range
  companion table already on the sheet** (MantCEN, MantLIN, MantEMB each have a second table to the
  right of the raw date-range input, already resolved to block/stage numbers — MantEMB's is even
  already volume-valued, not level/Cota) — no date→stage conversion logic needed for them at all.
  Only `MantEMBh` (→ `plpminembh.dat`) has just the raw date-range table, needing both date→stage
  conversion and the ported `Vol_<Name>` curves from Phase 0 (level→volume, further divided by
  1000 — a different, simpler, non-`f_esc`-dependent convention than `plpcnfce.dat`'s embalse
  volumes needed).

  `BatteryMaintenance` continues the "no Excel source" pattern (bootstrapped from the golden file,
  like Phase 2's reservoir curves) — and that golden file itself turned out to have an internal
  inconsistency (a declared per-battery row count that doesn't match its actual row count), fixed
  by making the bootstrap parser read until the next comment line rather than trusting the count.

  At this scale (`plpmance.dat` alone: 2,783 plants, ~610k rows), the live Excel data has
  measurably drifted from the checked-in golden snapshots in ways confirmed to be genuine case-data
  evolution, not bugs — extra/missing maintenance entries where the live sheet gained or dropped
  windows, single-cent rounding shifts at 0.005 boundaries, and (only for `plpmance.dat`, ~2% of
  rows) a handful of plants whose maintenance date ranges shifted enough to change which blocks are
  covered. Every test in this phase distinguishes that expected drift from an actual regression —
  see each `test_plpman*.py`'s comments for specifics.
- **Phase 5** — hydrology & inflows: `inflow`, `hydrology_scenario_assignment`,
  `aperture_index_simulation`, `aperture_index_aggregate`; generators for `plpaflce.dat` (172
  plants, ~40k rows — the golden file is 21.5MB, the largest single input file in the project),
  `plpidsim.dat`, `plpidape.dat`, `plpidap2.dat`.

  All four are bootstrapped straight from the golden files — this was the plan's own scoping from
  the start, not a shortcut found along the way: VBA's own `Rnd` PRNG (used for the "ALEATORIA"
  hydrology-scenario sampling in `Archivo_07`/`Archivo_12`/`Archivo_13`) can't be reproduced
  bit-for-bit in Python, so there was never a real algorithm to port here — these are plain
  editable data now (a future "regenerate scenarios" action could use Python's own `random`,
  explicitly not bit-compatible with old VBA runs, which is fine: these are stochastic draws, not
  something needing historical reproducibility). Multi-value fields (a plant-block's 65
  hydrology-class values, a stage's aperture-index list) are stored as JSON rather than one row
  per value, since they're always read/written as one unit.

  The only mismatch found: 2 plants in `plpaflce.dat` (`ALTOPOLC`, `Sum_Isla_Mina`) are classified
  `'X'` (fuera de servicio) in the current Centrales sheet and so have no active `Plant` row at
  all — same exclusion convention as `plpcnfce.dat` itself, not a new issue.
- **Phase 6** — basin conventions & remaining static files: `ralco_convention`,
  `extraction_point`, `reservoir_filtration`, `reservoir_spill_volume`, `basin_convention_line`;
  generators for `plpralco.dat`, `plpextrac.dat`, `plpfilemb.dat`, `plpvrebemb.dat`,
  `plpmaulen.dat`, `plplajam.dat`.

  Four of these six files (`plpralco.dat`/`plpextrac.dat`/`plpfilemb.dat`/`plpvrebemb.dat`) have
  **no Excel source in the current workbook at all** — confirmed by listing every sheet, hidden
  included: none of `RestRalco`/`EXTRACCIONES`/`FILTRACIONES`/`REBVERT` (the sheets the VBA writers
  reference) exist. Bootstrapped from the golden files, same mechanism as Phase 2's reservoir
  curves; still modeled as proper normalized tables (referencing `Plant`) since that's a natural
  fit for a real editing UI.

  `plpmaulen.dat`/`plplajam.dat` DO have real, current sheets (`MAULEN`/`LAJAM`) — but each is
  ~90-100 sequential fields of several different shapes (scalars, 12-month curves,
  variable-length name lists, "manual override by year" blocks whose row count can be zero), and
  both are rarely-edited basin operating agreements rather than per-case tunable data. A deliberate
  scoping choice, not a workaround: `BasinConventionLine` stores each file as its exact ordered
  sequence of physical lines (comment or data, tagged), replayed verbatim by the generator — still
  real editable data (each line is a plain editable text field), and correct by construction, since
  bootstrapping and regenerating is an exact round-trip with no transformation logic to get wrong.
- **Phase 7** — web UI completion & case management:
  - `case_clone.py`: generic case cloning. Rather than hand-writing copy/remap logic for the ~30
    domain tables (updating it every time a phase adds one), it walks
    `Base.metadata.sorted_tables` (SQLAlchemy's own FK-dependency topological order) and generically
    copies each table's rows, remapping foreign keys via an old-id -> new-id map built as it goes —
    including tables scoped only *transitively* (`reservoir.plant_id -> plant.case_id`, no direct
    `case_id` column) and the one self-referential FK (`Plant.downstream_gen/vert_plant_id`, fixed
    up in a second pass once the full plant id-map is known). Verified against every one of the
    ~30 tables: row counts match exactly, and the self-referential FK correctly re-targets the new
    case's own copy of the referenced plant, not the source case's.
  - Basin Conventions web UI (Ralco/Extraction/Filtration/SpillVolume tables, plus a per-line editor
    for the Maule/Laja convention files) — the one set of Phase 6 tables that hadn't gotten a UI yet.
  - A "Clone this case" action on the case overview page.

  Not attempted, and worth being explicit about rather than silently thin: a full CRUD editor for
  every bulk table (demand shapes, maintenance ranges, inflow curves, hydrology scenarios) — those
  are already covered by direct DB access and the generator pipeline, but a hundred-thousand-row
  table isn't a good fit for a plain HTML form either way; a dedicated grid UI for those is future
  work, not a gap in this phase's scope. Same for porting the VBA's own pre-generation validation
  checks (e.g. Archivo_06's future-cost-curve check) as inline web-form feedback — most of those
  guard files (`plpplaem.dat` and similar) that turned out to be out of scope for this case's
  active feature set in the first place (see Phase 2/6 notes above).

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

`--dat-static`/`--dat-block-dependant` are optional — omit either (or both) to import from the
`.xlsm` alone:

```
uv run python -m portal import-xlsm --name "new_case" --xlsm /path/to/new_case.xlsm
```

The handful of fields with no derivable Excel source (see "Known bootstrap limitations" below) then
fall back to sensible model defaults, or are left empty for tables with no plausible default (a
per-reservoir rating curve, hydrology data) — each fallback prints a warning so it's visible, not
silently assumed correct. Everything else — including all 234 block durations, now derived directly
from the Etapas sheet's own per-block hour-count columns rather than a golden file — imports fully
either way.

## Every case is its own SQLite file

Each case gets its own dedicated file under `cases/` (e.g. `cases/IPLP20251001_c00.sqlite3`),
named/created fresh by `import-xlsm` above — not a row alongside other cases in one shared
database. A tiny separate registry database (`cases/_registry.sqlite3`, see `db/registry.py`)
indexes which file each case_id lives in; it holds only id/name/description/file_name, never case
data itself, and can be reconstructed from the case files themselves if it's ever lost. Override
where cases live with `PORTAL_CASES_DIR` (defaults to `<project root>/cases/`). The web app's
"Clone" action copies the whole file and rewrites `case_id` in place (see `case_clone.clone_case_file`)
rather than copying rows within a shared database — `case_clone.clone_case` (the original,
row-by-row implementation) still exists as a library function for cloning *within* one multi-case
file, if that's ever needed again, and remains fully tested.

`db/session.py`'s `make_engine`/`DEFAULT_DB_PATH`/`portal.sqlite3` (override with `PORTAL_DB_PATH`)
are unrelated legacy single-file plumbing kept only because the test suite seeds one ad-hoc on-disk
database directly per test session — no longer what `import-xlsm` or the web app actually use.

**On the "second, transformed database" idea**: rather than a literal second SQLite file (xlsm ->
DB1 (editable) -> transform -> DB2 (computed) -> .dat), the same separation is achieved with one
database per case plus compute-on-demand generation — `generators/*.py` already compute every
derived value straight from DB1's raw/editable data at `.dat`-generation time (`demand_calc.py` is
the fullest example: it derives per-bus demand from DB1's normalized shapes + weekly targets on
every call, nothing precomputed and stored). A second physical database would mean keeping it in
sync with every edit made through the web UI — extra invalidation logic for no real benefit, since
regenerating a `.dat` file is already fast enough to do on demand.

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

The suite takes roughly a minute, mostly `demand_calc.compute()` (~10s per call, run twice — once
each for the `plpdem.dat` and `indhor.csv` tests). `web/routers/generate.py`'s "generate all" web
action shares one `compute()` call between both files instead of paying for it twice; the plain
per-file preview/test path doesn't, since each test should be able to run standalone.

## Recovering broken Excel formulas at import time

Real, currently-in-use workbooks were found to contain cached Excel formula-error strings
(`#NAME?`, `#REF!`, etc.) — typically because `FUNCCDEC_CDEC.xla` wasn't loaded at the last recalc,
so `=Vol_<Name>(cota)`/`=Rend_<Name>(cota)` cells (Centrales sheet's Volumen/Rendimiento columns)
cached an error instead of a number. `_safe_float()` tolerates any such cell everywhere in the
importer (logs a warning, falls back to `0.0`), but for these two specific columns the importer
does better than that default: `vol_or_from_cota()`/`rendimiento_or_from_cota()` recover the real
value from the paired (non-formula) Cota column using the exact same ported `Vol_<Name>`/
`Rend_<Name>` curves (`curves/reservoir_volume.py`/`reservoir_yield.py`) the broken formula itself
would have called — not every reservoir has a ported `Rend_<Name>` (e.g. `LMAULE` genuinely has
none in the source workbook), so that one case still falls back to `_safe_float`'s `0.0`.

## Known bootstrap limitations (tracked, not hidden)

A number of fields/tables are seeded from the case's *existing* golden `.dat` files, when given,
rather than derived from the `.xlsm` — see each `db/migrate_from_xlsm.py` import function's
docstring for the specific reason in each case. `--dat-static`/`--dat-block-dependant` are optional
(see "Import a case" above); with either omitted, these all fall back gracefully instead of
crashing — the fallback differs by situation:

1. **Genuinely out of scope so far**: `Stage.hydro_dependent`/`Stage.rate_factor` (deriving these
   needs VBA logic not ported in this project — `FactTasa` is a compounding per-stage discount
   factor) default to `False`/`1.0` with no golden `plpeta.dat`. `Block` durations are **no longer**
   in this category — they're now derived directly from the Etapas sheet's own per-block hour-count
   columns (confirmed to match the golden `plpblo.dat` exactly, all 234 blocks), so no golden file
   is needed for them at all, xlsm-alone or not.
2. **No Excel/VBA source exists at all**, confirmed by direct inspection (not assumed): the three
   solver-control files (each column defaults to the model's own default with no golden file —
   `db/models.py`'s `MathParams`/`DebugParams`/`RunParams` already have sensible per-column
   defaults), `Reservoir.f_esc` (defaults to `1.0`), all of `plpcenre.dat`/`plpcenpmax.dat`
   (Phase 2 — left empty, no plausible default for a per-reservoir piecewise curve); all of Phase
   5's hydrology tables (`plpaflce.dat`/`plpidsim.dat`/`plpidape.dat`/`plpidap2.dat` — VBA's own
   `Rnd` PRNG isn't reproducible, so there was never an algorithm to port, not just one left
   undone — left empty); `BatteryMaintenance` (Phase 4, left empty); `RalcoConvention`/
   `ExtractionPoint`/`ReservoirFiltration`/`ReservoirSpillVolume` (Phase 6 — the sheets the VBA
   writers reference don't exist anywhere in the current workbook, hidden sheets included — left
   empty). For these, "porting the derivation" doesn't mean anything — bootstrapping *is* the
   mechanism, since there's nowhere else this data could come from. A from-scratch, xlsm-alone case
   gets a usable case regardless (these fields/tables just start at a neutral default or empty,
   editable afterwards via the web UI), but genuinely needs this data supplied by hand (or from
   wherever it's actually maintained outside this workbook) before it's fully accurate.

`plpmaulen.dat`/`plplajam.dat` are a third, distinct case: real current sheets (`MAULEN`/`LAJAM`)
exist, but are stored as a verbatim line sequence rather than parsed field-by-field — a deliberate
scoping choice (see Phase 6 above), not a source limitation the same way the other two categories are.

Per the user's decision (2026-08-30): where this repo's `plp_cen` checkout of the solver disagrees
with a checked-in sample filename, **the code is the rule** — the sample's name is taken as the
error. This resolved the `plpmanbat.dat` (code) vs `plpmantbat.dat` (sample) mismatch flagged
after Phase 1: Phase 4's battery-maintenance generator writes `plpmanbat.dat`.
