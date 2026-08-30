from sqlalchemy import func, select

from portal.case_clone import clone_case
from portal.db.models import Base, Plant


def test_clone_case_matches_every_table_row_count(session, case_id):
    new_case = clone_case(session, case_id, "clone-test")
    session.flush()

    for table in Base.metadata.sorted_tables:
        if table.name == "case" or "case_id" not in table.columns:
            continue  # transitively-scoped tables (reservoir, *_segment, battery_injector) are
            # covered indirectly: if their parent table's rows didn't clone correctly, the
            # self-referential-FK check below (which depends on plant cloning correctly) would fail
        n_source = session.scalar(
            select(func.count()).select_from(table).where(table.c.case_id == case_id)
        )
        n_clone = session.scalar(
            select(func.count()).select_from(table).where(table.c.case_id == new_case.id)
        )
        assert n_source == n_clone, f"{table.name}: {n_source} source rows vs {n_clone} cloned"


def test_clone_case_remaps_self_referential_plant_fk(session, case_id):
    new_case = clone_case(session, case_id, "clone-test-2")
    session.flush()

    source_lmaule = session.scalars(
        select(Plant).where(Plant.case_id == case_id, Plant.name == "LMAULE")
    ).first()
    clone_lmaule = session.scalars(
        select(Plant).where(Plant.case_id == new_case.id, Plant.name == "LMAULE")
    ).first()
    assert clone_lmaule.downstream_gen_plant_id is not None
    assert clone_lmaule.downstream_gen_plant_id != source_lmaule.downstream_gen_plant_id
    target = session.get(Plant, clone_lmaule.downstream_gen_plant_id)
    assert target.case_id == new_case.id
