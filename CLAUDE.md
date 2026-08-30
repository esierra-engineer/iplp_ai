# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a **data repository for the PLP model** ("Planificación de Largo Plazo" / long-term operation
planning), a hydrothermal dispatch/coordination model used for the Chilean electric system (SIC/CDEC
context — see the `.xla` metadata: "Funciones de Embalses y Centrales del SIC", "Interfaz EXCEL Modelo
PLP"). There is no application source code here — it is inputs and the Excel tooling that produces them:

- `xlsm/IPLP20251001_c00.xlsm` — the Excel **interface workbook**. Analysts enter case data here across
  named sheets (demand, buses, lines, plants/reservoirs, maintenance, hydrology, etc.).
- `xla/MacroPLP_I_20250508.xla` — Excel add-in ("Macro PLP - Crea archivos DAT") containing the VBA
  macros that read the `.xlsm` sheets and write out the `dat/*.dat` input files consumed by the external
  PLP solver (the solver binary itself is not part of this repo).
- `xla/FUNCCDEC_CDEC.xla` — Excel add-in of supporting functions for CDEC-style reservoir/plant
  calculations, used by the macros above.
- `dat/` — the generated fixed-format text input files for a specific PLP run/case (this snapshot is
  named after `IPLP20251001`, i.e. a case starting October 2025).

There is no build, lint, or test tooling in this repo (no package manifest, no CI config). "Development"
here means editing case data in the `.xlsm`, regenerating `.dat` files via the VBA macros in Excel, and/or
hand-editing the generated `.dat` files.

## Editing workflow

1. Open `xlsm/IPLP20251001_c00.xlsm` in Excel with both `.xla` add-ins loaded/installed.
2. Edit the relevant input sheet(s) (see mapping below).
3. Run the corresponding `Archivo_NN_...` macro from `MacroPLP_I_*.xla` to regenerate the affected
   `.dat` file(s) into `dat/`.
4. If hand-editing a `.dat` file directly instead, preserve the exact fixed-width/column layout and the
   leading `#`-comment header lines — the PLP solver parses these files positionally, not by header text.

The VBA modules in `MacroPLP_I_*.xla` are numbered and named after the output file they produce, e.g.:

| Module | Output file |
|---|---|
| `Archivo_01_PLPBAR` | `plpbar.dat` |
| `Archivo_02_PLPETA` (+`_BE`/`_CSV`/`_PRN`) | `plpeta.dat` |
| `Archivo_03_PLPDEM` | `plpdem.dat` |
| `Archivo_04_PLPCEN` | `plpcnfce.dat` |
| `Archivo_05_PLPLIN` | `plpcnfli.dat` |
| `Archivo_06_PLPEMB` | `plpplem1.dat`/`plpplem2.dat` |
| `Archivo_07_PLPAFL`/`AFLU4S` | `plpaflce.dat` |
| `Archivo_08_PLPCOSCE` | `plpcosce.dat` |
| `Archivo_09_PLPMANCE*` | `plpmance.dat` |
| `Archivo_10_PLPMANLI*` | `plpmanli.dat` |
| `Archivo_11_PLPMANEM*` | `plpmanem.dat` |
| `Archivo_12_PLPIDSIM` | `plpidsim.dat` |
| `Archivo_13_PLPIDAPE` | `plpidape.dat` (and `plpidap2.dat`) |
| `Archivo_14_PLPMAULE*` / `ARCHIVO_30_PLPMAULEN` | `plpmaulen.dat` |
| `Archivo_15_PLPLAJA*` / `ARCHIVO_31_PLPLAJAM` | `plplajam.dat` |
| `ARCHIVO_16_PLPEXTRAC` | `plpextrac.dat` |
| `ARCHIVO_17_PLPFILTEMB` | `plpfilemb.dat` |
| `ARCHIVO_18_PLPVREVEMB` | `plpvrebemb.dat` |
| `ARCHIVO_20_PLPRALCO` | `plpralco.dat` |
| `ARCHIVO_32_PLPMINEMBH` | `plpminembh.dat` |
| `ARCHIVO_36_PLPCENBAT` | `plpcenbat.dat` |

When asked to change how a given `.dat` file is generated, find the matching module name in
`MacroPLP_I_*.xla` — do not guess at a mapping not listed above without checking the module list first
(`Module=` strings in the file).

The `.xlsm` sheet names give the input side of the same mapping, e.g. `Barras`→bus data, `Demanda-*`→load,
`Líneas`/`MantLIN`→transmission lines and outages, `Centrales`/`CV_CP`/`CV_MP`→plant variable costs,
`Embalses`/`Caudales_*`/`Hidrología`→reservoirs and inflows/hydrology scenarios, `MantCEN`/`MantEMB*`→
maintenance schedules, `Baterias`→battery storage, `LAJAM`/`MAULEN`→special basin operating agreements
(Laja and Maule river conventions).

## `dat/` directory structure

- `dat/static/` — inputs that describe the fixed topology/configuration of the system for this case:
  buses (`plpbar.dat`), lines (`plpcnfli.dat`), plant configuration (`plpcnfce.dat`), reservoir
  polynomials/curves (`plpcenre.dat`, `plpcenpmax.dat`), batteries (`plpcenbat.dat`), basin conventions
  (`plplajam.dat`, `plpmaulen.dat`, `plpralco.dat`), solver/debug/math parameters (`plpmat.dat`,
  `plpdeb.dat`, `plprun.dat`), etc.
- `dat/block_dependant/` — inputs that vary per time block/stage (`Bloque`/`Etapa`) for this case's
  horizon: demand (`plpdem.dat`), inflows (`plpaflce.dat`), thermal variable costs (`plpcosce.dat`),
  maintenance schedules (`plpmance.dat`, `plpmanli.dat`, `plpmanem.dat`, `plpmantbat.dat`,
  `plpminembh.dat`), hydrology scenario indices (`plpidsim.dat`, `plpidape.dat`, `plpidap2.dat`), and
  block/stage duration tables (`plpblo.dat`, `plpeta.dat`, `indhor.csv`).

## `.dat` file format conventions

All `.dat` files share the same shape and must be read/edited with this in mind:

- Lines starting with `#` are human-readable comment/header lines describing the *next* data line(s) —
  they are documentation, not something the parser skips generically; column meaning is defined by
  position, and comment wording is not always accurate to number of columns (verify against actual data
  rows when unsure).
- Data is whitespace/fixed-column aligned Fortran-style tabular text (quantities right-aligned, names in
  `'single quotes'`), or occasionally plain CSV (e.g. `plpplem2.dat`, `indhor.csv`).
- Most files are organized as repeating blocks: a count line, then that many records, where each record
  itself starts with a name/id line followed by a sub-count and a table of `Mes`/`Etapa`/`Bloque`-indexed
  values (e.g. one block per power plant, reservoir, line, or bus).
- Encoding is inconsistent across files — some are plain ASCII, some ISO-8859-1 (accented Spanish text,
  e.g. `plpcenre.dat`, `plplajam.dat`, `plpmaulen.dat`), one is UTF-8 (`plpvrebemb.dat`). Preserve a
  file's existing encoding when editing it rather than normalizing to UTF-8.
- `Etapa` (stage) and `Bloque` (block) numbering must stay consistent across files for a given case:
  `plpeta.dat` and `plpblo.dat` define the stage/block calendar (which month/hours each stage and block
  covers) that all other `block_dependant` files index into by stage or block number.

## Working with the Excel files

`.xla`/`.xlsm` are binary OLE/OOXML files — do not attempt to view or diff them as text. To inspect
structure programmatically: `.xlsm` files are zip archives (`unzip -l`, then read `xl/workbook.xml` for
sheet names); VBA source inside `.xla`/`.xlsm` can be listed/extracted with tools like `oletools`
(`olevba`) if available, but is not installed by default in this environment.
