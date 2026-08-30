"""Generic case cloning.

`clone_case` (below) duplicates every table's rows for one case into a *new case row in the same
database* — still useful as a library capability (e.g. merging one case into an existing
multi-case file), and still fully tested, but no longer what the web UI's "clone" action uses.
`clone_case_file`, at the bottom of this module, is what the web UI uses now that every case is its
own SQLite file (see db/registry.py): it copies the whole file and rewrites `case_id` in place,
which is simpler and cheaper than row-by-row copying since every *other* primary key can stay
exactly as-is — a raw file copy already gives every child row a byte-identical copy.

Original `clone_case` docstring, still accurate for that function: duplicate every table's rows for
one case into a new case.

Rather than hand-writing per-table copy/remap logic for the ~30 domain tables (which would need
updating every time a phase adds a table), this walks `Base.metadata.sorted_tables` — SQLAlchemy's
own topological ordering by foreign-key dependency — and generically copies each table's rows for
the source case, remapping any foreign key that points at a row we've already cloned in this same
pass (using an old-id -> new-id map recorded per table). This only works because every domain
table is scoped to a case either directly (a `case_id` column) or transitively (a foreign key to a
table that is itself scoped to the case, e.g. `reservoir.plant_id` -> `plant.case_id`) — true
throughout this schema.

Two primary-key shapes need special handling, detected generically rather than hardcoded per
model: most tables have a plain autoincrement `id`; a few (MathParams, DebugParams, RunParams,
LineConfig) use `case_id` itself as the primary key; `Reservoir` uses `plant_id` as its primary
key (remapped via the `plant` table's id map, not its own — handled by the same transitive-scoping
logic as the "no case_id" tables below).
"""

from __future__ import annotations

import shutil

from sqlalchemy import Table, create_engine, insert, select, update
from sqlalchemy.orm import Session

from .db.models import Base, Case
from .db.registry import register_case, resolve_case_path


def clone_case(session: Session, source_case_id: int, new_name: str, description: str | None = None) -> Case:
    source = session.get(Case, source_case_id)
    if source is None:
        raise ValueError(f"no case with id {source_case_id}")

    new_case = Case(name=new_name, description=description or f"Cloned from {source.name!r}")
    session.add(new_case)
    session.flush()  # assign new_case.id

    # old_id -> new_id, per table name, for every table whose PK is a plain "id" column. Tables
    # keyed by something else (case_id, plant_id) aren't referenced by their own id elsewhere, so
    # they don't need an entry here.
    id_maps: dict[str, dict[int, int]] = {}

    for table in Base.metadata.sorted_tables:
        if table.name == "case":
            continue

        pk_cols = list(table.primary_key.columns)
        pk_is_plain_id = len(pk_cols) == 1 and pk_cols[0].name == "id"

        if "case_id" in table.columns:
            rows = session.execute(
                select(table).where(table.c.case_id == source_case_id)
            ).mappings().all()
            scope_col = "case_id"
            scope_new_value = new_case.id
        else:
            # Transitively scoped (e.g. reservoir.plant_id -> plant.case_id): find the FK column
            # whose target table we've already cloned, and select rows whose FK value is one of
            # that table's OLD ids (i.e. belonged to the source case).
            scope_col, target_table = _find_scoping_fk(table, id_maps)
            if scope_col is None:
                continue  # no scoping FK found (shouldn't happen in this schema) — skip safely
            old_ids = list(id_maps[target_table].keys())
            if not old_ids:
                continue
            rows = session.execute(
                select(table).where(table.c[scope_col].in_(old_ids))
            ).mappings().all()
            scope_new_value = None  # remapped per-row below, like any other FK

        if not rows:
            continue

        new_rows = []
        this_table_id_map: dict[int, int] = {}
        for row in rows:
            new_row = dict(row)
            if scope_new_value is not None:
                new_row[scope_col] = scope_new_value
            old_pk = new_row.get("id") if pk_is_plain_id else None
            if pk_is_plain_id:
                del new_row["id"]

            for fk in table.foreign_keys:
                col_name = fk.parent.name
                target_table = fk.column.table.name
                if target_table == "case" or col_name not in new_row or new_row[col_name] is None:
                    continue
                target_map = id_maps.get(target_table)
                if target_map is not None and new_row[col_name] in target_map:
                    new_row[col_name] = target_map[new_row[col_name]]
                # else: self-referential or forward reference — fixed up in the second pass below.

            new_rows.append((old_pk, new_row))

        for old_pk, new_row in new_rows:
            result = session.execute(insert(table).values(**new_row))
            if pk_is_plain_id:
                this_table_id_map[old_pk] = result.inserted_primary_key[0]

        if pk_is_plain_id:
            id_maps[table.name] = this_table_id_map

    session.flush()
    _fix_self_referential_fks(session, id_maps)
    return new_case


def clone_case_file(source_case_id: int, new_name: str, description: str | None = None) -> int:
    """One-file-per-case cloning: allocate a new case_id + file via the registry, copy the source
    case's file byte-for-byte, then rewrite every `case_id` column (including the "case" table's
    own `id`, and the handful of tables — MathParams/DebugParams/RunParams/LineConfig — where
    case_id itself is the primary key) from the old id to the new one. No other primary key needs
    remapping: the file copy already gave every other row (plant.id, bus.id, ...) an identical,
    still-internally-consistent copy. Returns the new case_id."""
    source_path = resolve_case_path(source_case_id)
    if source_path is None or not source_path.exists():
        raise ValueError(f"no case with id {source_case_id}")

    new_id, new_path = register_case(new_name, description)
    shutil.copy2(source_path, new_path)

    engine = create_engine(f"sqlite:///{new_path}", future=True)
    try:
        with engine.begin() as conn:
            case_table = Base.metadata.tables["case"]
            conn.execute(
                update(case_table)
                .where(case_table.c.id == source_case_id)
                .values(
                    id=new_id,
                    name=new_name,
                    description=description or f"Cloned from case {source_case_id}",
                )
            )
            for table in Base.metadata.sorted_tables:
                if table.name == "case" or "case_id" not in table.columns:
                    continue
                conn.execute(
                    update(table).where(table.c.case_id == source_case_id).values(case_id=new_id)
                )
    finally:
        engine.dispose()

    return new_id


def _find_scoping_fk(table: Table, id_maps: dict[str, dict[int, int]]) -> tuple[str | None, str | None]:
    """For a table with no direct case_id column, find its first foreign key column whose target
    table has already been cloned (so we know which old ids belong to the source case)."""
    for fk in table.foreign_keys:
        target_table = fk.column.table.name
        if target_table in id_maps:
            return fk.parent.name, target_table
    return None, None


def _fix_self_referential_fks(session: Session, id_maps: dict[str, dict[int, int]]) -> None:
    """Second pass: self-referential FKs (currently only Plant.downstream_gen_plant_id /
    downstream_vert_plant_id) may reference a row inserted later in the same table's copy loop —
    fix them up now that the full old->new id map for that table is known."""
    plant_table: Table = Base.metadata.tables["plant"]
    plant_map = id_maps.get("plant")
    if not plant_map:
        return
    for col_name in ("downstream_gen_plant_id", "downstream_vert_plant_id"):
        rows = session.execute(
            select(plant_table.c.id, plant_table.c[col_name]).where(
                plant_table.c.id.in_(plant_map.values()), plant_table.c[col_name].isnot(None)
            )
        ).all()
        for new_plant_id, current_value in rows:
            # current_value is still the OLD plant id (copied verbatim in the first pass since the
            # target row didn't have a new id yet) — remap it now.
            if current_value in plant_map:
                session.execute(
                    plant_table.update()
                    .where(plant_table.c.id == new_plant_id)
                    .values(**{col_name: plant_map[current_value]})
                )
    session.flush()
