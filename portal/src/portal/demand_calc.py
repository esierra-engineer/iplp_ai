"""Port of Rutina04.DEMxBarra2 (per-bus demand disaggregation) + the block-aggregation loop shared
by Archivo_03_PLPDEM_5A's `plpdem.dat`/`indhor.csv` output — see the plan/session notes for how
this was traced out of the VBA source. This module implements the algorithm once; both
generators/plpdem.py and generators/indhor.py call `compute()` and read off what they need.

Algorithm (mirroring the VBA exactly, for this case's actual runtime path — CDECSimTyp=0,
Etapas!K1="mensual"):

1. Normalized per-(bus, category, month, day-type, hour) load shape comes straight from
   DemandProfile (imported from the Demanda-R/L/LD sheets).
2. Every calendar day has a day-type: 1=Domingo, 2=Lunes, 3=Sabado, 4=Trabajo(Tue-Fri) — Sundays
   AND holidays both map to 1 (a listed holiday overrides its actual weekday).
3. For each ConsumptionWeek overlapping the case's stage horizon, sum the shape values across all
   buses/days-in-week/hours per category to get DemHist (GWh), then
   DemFC = gwh_target / DemHist (0 if gwh_target is 0 — the VBA zeroes that category's demand
   entirely for the week rather than dividing by it).
4. Per (bus, day, hour): demand = sum over R/L/LD of shape * that week's DemFC for that category,
   PLUS any IndustrialProject's flat MW covering that day and bus (added unscaled, after step 3's
   scaling — matches CDECSimTyp=0's "Incorpora los nuevos consumos... cuando corresponde" branch —
   and only when that week's 'L' (Libre) target isn't itself zero, same zero-guard as the VBA).
5. Blocks are assigned chronologically (not sorted by load level — that's the INGHORAS-mode-only
   duration-curve path in the VBA, which this case's "mensual" mode does not take): within a
   stage, the first Block's `duration` hours (in day/hour order) are block 1, the next Block's
   hours are block 2, and so on. Each (bus, block) demand is the mean of that block's hours.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db.models import Block, ConsumptionWeek, DemandProfile, Holiday, IndustrialProject, Stage


def day_type(d: date, holidays: set[date]) -> int:
    if d in holidays:
        return 1
    wd = d.weekday()  # Monday=0 .. Sunday=6
    if wd == 6:
        return 1  # Domingo
    if wd == 0:
        return 2  # Lunes
    if wd == 5:
        return 3  # Sabado
    return 4  # Trabajo (Tue-Fri)


@dataclass
class DemandResult:
    # (bus_id, num_blo) -> mean MW over that block's hours
    bar_block_mw: dict[tuple[int, int], float] = field(default_factory=dict)
    # (year, month, day, hour 1-24) -> num_blo, in chronological order (for indhor.csv)
    hour_to_block: list[tuple[int, int, int, int, int]] = field(default_factory=list)
    num_blo_total: int = 0


def compute(session: Session, case_id: int) -> DemandResult:
    stages = session.scalars(
        select(Stage).where(Stage.case_id == case_id).order_by(Stage.num_eta)
    ).all()
    if not stages:
        return DemandResult()

    blocks_by_stage: dict[int, list[Block]] = defaultdict(list)
    for b in session.scalars(
        select(Block).where(Block.case_id == case_id).order_by(Block.num_blo)
    ):
        blocks_by_stage[b.stage_id].append(b)

    bus_ids = [
        row[0]
        for row in session.execute(
            select(DemandProfile.bus_id).where(DemandProfile.case_id == case_id).distinct()
        )
    ]

    # Bulk-load the shape table as plain tuples (ORM object construction for ~480k rows is
    # unnecessarily slow and memory-heavy for a lookup table we only ever read).
    shape: dict[tuple[int, str, int, int, int], float] = {}
    for bus_id, category, month, dtype, hour, mw in session.execute(
        select(
            DemandProfile.bus_id,
            DemandProfile.category,
            DemandProfile.month,
            DemandProfile.day_type,
            DemandProfile.hour,
            DemandProfile.mw,
        ).where(DemandProfile.case_id == case_id)
    ):
        shape[(bus_id, category, month, dtype, hour)] = mw

    holidays = {
        h[0] for h in session.execute(select(Holiday.date).where(Holiday.case_id == case_id))
    }
    weeks = session.scalars(
        select(ConsumptionWeek).where(ConsumptionWeek.case_id == case_id).order_by(
            ConsumptionWeek.week_num
        )
    ).all()
    projects = session.scalars(
        select(IndustrialProject).where(IndustrialProject.case_id == case_id)
    ).all()
    projects_by_bus: dict[int, list[IndustrialProject]] = defaultdict(list)
    for p in projects:
        projects_by_bus[p.bus_id].append(p)

    horizon_start = min(s.start_date for s in stages)
    horizon_end = max(s.start_date + timedelta(days=s.duration // 24 - 1) for s in stages)

    # --- Step 3: per-week DemFC(category), only for weeks overlapping the study horizon ---
    demfc: dict[int, dict[str, float]] = {}
    week_target: dict[int, dict[str, float]] = {}
    for wk in weeks:
        wk_end = wk.start_date + timedelta(days=wk.num_days - 1)
        if wk_end < horizon_start or wk.start_date > horizon_end:
            continue
        target = {"R": wk.gwh_r, "L": wk.gwh_l, "LD": wk.gwh_ld}
        week_target[wk.week_num] = target
        hist_mwh = dict.fromkeys(("R", "L", "LD"), 0.0)
        for i in range(wk.num_days):
            d = wk.start_date + timedelta(days=i)
            dtype = day_type(d, holidays)
            for bus_id in bus_ids:
                for cat in ("R", "L", "LD"):
                    for hour in range(1, 25):
                        hist_mwh[cat] += shape.get((bus_id, cat, d.month, dtype, hour), 0.0)
        factors = {}
        for cat in ("R", "L", "LD"):
            hist_gwh = hist_mwh[cat] / 1000.0
            factors[cat] = (target[cat] / hist_gwh) if hist_gwh else 0.0
        demfc[wk.week_num] = factors

    week_num_by_date: dict[date, int] = {}
    for wk in weeks:
        wk_end = wk.start_date + timedelta(days=wk.num_days - 1)
        if wk_end < horizon_start or wk.start_date > horizon_end:
            continue
        for i in range(wk.num_days):
            week_num_by_date[wk.start_date + timedelta(days=i)] = wk.week_num

    # --- Steps 4-5: per-stage, per-day, per-hour, per-bus demand, aggregated into blocks ---
    result = DemandResult()
    for stage in stages:
        blocks = blocks_by_stage[stage.id]
        num_dias = stage.duration // 24

        # Blocks are NOT chronological chunks of the whole stage — each calendar day is sliced
        # into the same block pattern, repeating identically every day of the stage (confirmed
        # against the golden indhor.csv: e.g. a 7-day, 168-hour stage with 10 blocks summing to
        # 168 actually means each day is split 14/7=2h, 28/7=4h, 14/7=2h, ... — 10 slices summing
        # to 24h, the same every day). `hour_block_idx[h-1]` gives the block INDEX (0-based, into
        # `blocks`) for hour-of-day `h`, identical for every day in this stage.
        daily_hours = [b.duration / num_dias for b in blocks]
        hour_block_idx: list[int] = []
        acc = 0.0
        blk_i = 0
        for _h in range(24):
            while acc + 1e-9 >= daily_hours[blk_i] and blk_i < len(blocks) - 1:
                acc -= daily_hours[blk_i]
                blk_i += 1
            hour_block_idx.append(blk_i)
            acc += 1
        # ^ walks 24 one-hour steps, advancing to the next block once the current block's
        # per-day hour allowance is exhausted (small epsilon guards float accumulation).

        sums: dict[tuple[int, int], float] = defaultdict(float)  # (bus_id, num_blo) -> sum MW
        for day_idx in range(num_dias):
            d = stage.start_date + timedelta(days=day_idx)
            wk_num = week_num_by_date.get(d)
            factors = demfc.get(wk_num, {"R": 0.0, "L": 0.0, "LD": 0.0})
            target = week_target.get(wk_num, {"R": 0.0, "L": 0.0, "LD": 0.0})
            dtype = day_type(d, holidays)
            for hour in range(1, 25):
                num_blo = blocks[hour_block_idx[hour - 1]].num_blo
                for bus_id in bus_ids:
                    mw = 0.0
                    for cat in ("R", "L", "LD"):
                        mw += shape.get((bus_id, cat, d.month, dtype, hour), 0.0) * factors[cat]
                    for proj in projects_by_bus.get(bus_id, ()):
                        if proj.start_date <= d <= proj.end_date and target["L"] != 0:
                            mw += proj.demand_mw
                    sums[(bus_id, num_blo)] += mw
                result.hour_to_block.append((d.year, d.month, d.day, hour, num_blo))

        for (bus_id, num_blo), total in sums.items():
            blk = next(b for b in blocks if b.num_blo == num_blo)
            result.bar_block_mw[(bus_id, num_blo)] = total / blk.duration

    result.num_blo_total = max((b.num_blo for blist in blocks_by_stage.values() for b in blist), default=0)
    return result
