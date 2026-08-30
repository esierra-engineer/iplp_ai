"""SQLAlchemy models.

Normalized schema: canonical reference tables (``Case``, ``Stage``, ``Block``, ``Bus``, ``Line``,
and later ``Plant``/``Reservoir``) are referenced by foreign key everywhere instead of repeating
names. Every table is scoped by ``case_id`` so multiple PLP cases can live in one database.

This module currently covers Phase 1 (calendar & topology) plus the three simple solver-control
files pulled forward into Phase 1 (plpmat.dat, plpdeb.dat, plprun.dat), and Phase 2 (plant fleet:
plpcnfce.dat, plpcenre.dat, plpcenpmax.dat, plpcenbat.dat). Later phases add demand, maintenance,
hydrology, and basin-convention tables here following the same pattern.
"""

from __future__ import annotations

from datetime import date as _date

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Case(Base):
    """Top-level scenario/version key. Every other table is scoped by case_id."""

    __tablename__ = "case"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(String, default=None)

    stages: Mapped[list["Stage"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    blocks: Mapped[list["Block"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    buses: Mapped[list["Bus"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    lines: Mapped[list["Line"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Stage(Base):
    """One row per 'Etapa' — plpeta.dat. Order is significant (NumEta = 1..NEtapa, in row order)."""

    __tablename__ = "stage"
    __table_args__ = (UniqueConstraint("case_id", "num_eta"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    num_eta: Mapped[int] = mapped_column(Integer)  # 1-based position within the case, in file order
    year: Mapped[int] = mapped_column(Integer)  # calendar year, e.g. 2025 (NOT plpeta.dat's "Ano")
    month: Mapped[int] = mapped_column(Integer)  # calendar month 1-12 (NOT plpeta.dat's "Mes")
    hydro_dependent: Mapped[bool] = mapped_column(Boolean)  # FDesh: T/F
    duration: Mapped[int] = mapped_column(Integer)  # NHoras — INTEGER, not float (see spec)
    rate_factor: Mapped[float] = mapped_column(Float, default=1.0)  # FactTasa
    label: Mapped[str] = mapped_column(String, default="")  # TipoEtapa, e.g. '10 Bloques'
    start_date: Mapped[_date] = mapped_column(Date)  # Etapas!Inicial — needed for Phase 3's
    # day-by-day demand walk (num_dias = duration // 24, so no separate column for that).

    # NOTE on plpeta.dat's "Ano"/"Mes" columns: these are NOT the calendar year/month above. The
    # solver uses an April-start fiscal calendar (confirmed by cross-referencing the VBA maintenance
    # writers' "Month-3, +12 if <=0" convention against this case's own golden plpeta.dat): fiscal
    # month = calendar_month - 3 if calendar_month >= 4 else calendar_month + 9, and fiscal year
    # increments every time the case crosses an April boundary, counted from the case's first stage.
    # generators/plpeta.py derives both from the calendar (year, month) stored here — see that
    # module for the exact formula and its cross-check against this case's sample data.

    case: Mapped[Case] = relationship(back_populates="stages")
    blocks: Mapped[list["Block"]] = relationship(back_populates="stage")


class Block(Base):
    """One row per 'Bloque' — plpblo.dat. Optional file: a case may have no blocks (1:1 with stages)."""

    __tablename__ = "block"
    __table_args__ = (UniqueConstraint("case_id", "num_blo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    num_blo: Mapped[int] = mapped_column(Integer)  # 1-based, strictly in row order (reader enforces this)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stage.id"))
    duration: Mapped[float] = mapped_column(Float)  # DurBlo, hours
    # Decorative-only columns the Fortran reader never consumes, kept for human/tooling readability:
    year: Mapped[int] = mapped_column(Integer, default=1)
    month: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str] = mapped_column(String, default="")

    case: Mapped[Case] = relationship(back_populates="blocks")
    stage: Mapped[Stage] = relationship(back_populates="blocks")


class Bus(Base):
    """plpbar.dat — one row per 'Barra'."""

    __tablename__ = "bus"
    __table_args__ = (UniqueConstraint("case_id", "num_bar"), UniqueConstraint("case_id", "name"))

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    num_bar: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)

    case: Mapped[Case] = relationship(back_populates="buses")


class Line(Base):
    """plpcnfli.dat — transmission line config (maintenance is a separate table, added in Phase 4)."""

    __tablename__ = "line"
    __table_args__ = (UniqueConstraint("case_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    name: Mapped[str] = mapped_column(String)
    bus_from_id: Mapped[int] = mapped_column(ForeignKey("bus.id"))
    bus_to_id: Mapped[int] = mapped_column(ForeignKey("bus.id"))
    capacity_ab: Mapped[float] = mapped_column(Float)  # LinAB
    capacity_ba: Mapped[float] = mapped_column(Float)  # LinBA
    voltage_kv: Mapped[float] = mapped_column(Float)  # LinVNom
    resistance: Mapped[float] = mapped_column(Float)  # LinRes
    reactance: Mapped[float] = mapped_column(Float)  # LinXImp
    models_losses: Mapped[bool] = mapped_column(Boolean, default=True)  # LinFPer
    num_segments: Mapped[int] = mapped_column(Integer, default=1)  # LinNFlu (loss-model segments)
    operational: Mapped[bool] = mapped_column(Boolean, default=True)  # FOpe
    is_hvdc: Mapped[bool | None] = mapped_column(Boolean, default=None)  # optional 12th field, see spec

    case: Mapped[Case] = relationship(back_populates="lines")
    bus_from: Mapped[Bus] = relationship(foreign_keys=[bus_from_id])
    bus_to: Mapped[Bus] = relationship(foreign_keys=[bus_to_id])


class LineConfig(Base):
    """The one file-level header row of plpcnfli.dat (applies to all lines in the case)."""

    __tablename__ = "line_config"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    models_losses_globally: Mapped[bool] = mapped_column(Boolean, default=True)  # FPerdTram
    loss_model_in_erm: Mapped[str] = mapped_column(String, default="M")  # FPerdLin: 'E'/'R'/'M'
    reference_angle: Mapped[float] = mapped_column(Float, default=1000.0)  # ThetaRef


class MathParams(Base):
    """plpmat.dat — one row per case (solver math parameters)."""

    __tablename__ = "math_params"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    pd_max_iter: Mapped[int] = mapped_column(Integer, default=10)
    pd_error: Mapped[float] = mapped_column(Float, default=0.001)
    umb_int_conf: Mapped[float] = mapped_column(Float, default=0.001)
    pm_max_iter: Mapped[int] = mapped_column(Integer, default=10)
    pm_error: Mapped[float] = mapped_column(Float, default=5.0)
    lambda_: Mapped[float] = mapped_column("lambda", Float, default=0.0)
    c_tasa: Mapped[float] = mapped_column(Float, default=0.0)
    c_caudal_falla: Mapped[float] = mapped_column(Float, default=7000.0)
    c_vertimiento: Mapped[float] = mapped_column(Float, default=0.01)
    c_inter: Mapped[float] = mapped_column(Float, default=0.01)
    c_transmision: Mapped[float] = mapped_column(Float, default=0.01)
    f_vol_fin_emb: Mapped[bool] = mapped_column(Boolean, default=False)
    f_pre_proc: Mapped[bool] = mapped_column(Boolean, default=False)
    f_previa: Mapped[bool] = mapped_column(Boolean, default=False)
    f_fix_trasm: Mapped[bool] = mapped_column(Boolean, default=True)
    f_separa_fcf: Mapped[bool] = mapped_column(Boolean, default=False)
    f_graba_csv: Mapped[bool] = mapped_column(Boolean, default=False)
    f_graba_res: Mapped[bool] = mapped_column(Boolean, default=False)
    ab_max: Mapped[int] = mapped_column(Integer, default=50)
    ab_epsilon: Mapped[float] = mapped_column(Float, default=0.0)
    num_eta_cf: Mapped[int] = mapped_column(Integer, default=0)
    f_conv_pgradx: Mapped[bool] = mapped_column(Boolean, default=False)
    f_conv_pvar: Mapped[bool] = mapped_column(Boolean, default=False)
    umb_gradx: Mapped[float] = mapped_column(Float, default=0.0)
    umb_zspf: Mapped[float] = mapped_column(Float, default=0.0)


class DebugParams(Base):
    """plpdeb.dat — one row per case (solver debug/logging flags)."""

    __tablename__ = "debug_params"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    f_log: Mapped[bool] = mapped_column(Boolean, default=True)
    pri_prog_din: Mapped[bool] = mapped_column(Boolean, default=True)
    pd_sv_fl: Mapped[bool] = mapped_column(Boolean, default=False)
    pm_sv_fl: Mapped[bool] = mapped_column(Boolean, default=False)
    f_dat_che: Mapped[bool] = mapped_column(Boolean, default=False)
    er_sv_fl: Mapped[bool] = mapped_column(Boolean, default=True)
    ps_fz_fl: Mapped[bool] = mapped_column(Boolean, default=True)
    ft_sv_fl: Mapped[bool] = mapped_column(Boolean, default=False)
    f_sv_la_ps: Mapped[bool] = mapped_column(Boolean, default=False)
    ind_sim_imp: Mapped[int] = mapped_column(Integer, default=0)
    ind_ite_imp: Mapped[int] = mapped_column(Integer, default=0)
    f_best: Mapped[bool] = mapped_column(Boolean, default=False)  # solver always forces this back to F
    ind_eta1_imp: Mapped[int] = mapped_column(Integer, default=0)
    ind_eta2_imp: Mapped[int] = mapped_column(Integer, default=0)


class RunParams(Base):
    """plprun.dat — one row per case (hot-start control). Fully optional at the solver level."""

    __tablename__ = "run_params"

    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"), primary_key=True)
    plane_file: Mapped[str] = mapped_column(String, default="plpplanos.csv")
    iter_beg: Mapped[int] = mapped_column(Integer, default=0)
    iter_end: Mapped[int] = mapped_column(Integer, default=9999)
    open_mode: Mapped[int] = mapped_column(Integer, default=0)  # 0=no cuts, 1=read, 2=append


# =================================================================================================
# Phase 2 — plant fleet
# =================================================================================================
#
# PLANT_TYPES below matches the Fortran type-code constants in pxp.fpp exactly (E/A/S/R/P/T/B/F —
# see leecnfce.f cross-read): 'EMBALSE' and 'SERIE' each cover two file type-codes distinguished
# purely by whether bus_id is set (EMBALSE: bus set->'E', unset->'A' aux-embalse; SERIE: bus
# set->'S', unset->'R' riego) — see generators/plpcnfce.py. Plants classified 'X' (fuera de
# servicio) in the Centrales sheet are not imported at all, matching the VBA writer's own count
# ("total centrales, types 1-6 only, excludes X").
PLANT_TYPES = ("EMBALSE", "SERIE", "PASADA", "TERMICA", "BATERIA", "FALLA")


class Plant(Base):
    """One record of plpcnfce.dat. Several fields are read by the solver's leecnfce.f but never
    actually retained past that read (confirmed by reading the Fortran source directly, not just
    inferred from the file format): cen_ipot, min_tec, inter, fcad, mttd_hrz, p_ini, cost_arranque,
    cost_detencion, on_flag. Stored anyway for file round-trip fidelity — a future solver version
    (or other tooling) may use them, and they're real columns in the golden file's header."""

    __tablename__ = "plant"
    # name is NOT unique per case: the real Centrales sheet has duplicate-named FALLA (unserved-
    # energy tranche) plants — confirmed in this case's own data, not a modeling choice — so only
    # cen_ind (the file's own cross-reference key) is guaranteed unique.
    __table_args__ = (UniqueConstraint("case_id", "cen_ind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    cen_ind: Mapped[int] = mapped_column(Integer)  # "INDICE" — preserved verbatim from import: other
    # plants' downstream_gen/vert references resolve against this exact number, and the golden file
    # itself was written with these values, so regenerating a fresh sequence would break parity.
    # Also doubles as the file's within-block ordering key: confirmed (by parsing the golden file)
    # that cen_ind is strictly ascending within each type-block in file order, so `ORDER BY cen_ind`
    # per block reproduces the original record order without needing a separate sheet-row field.
    name: Mapped[str] = mapped_column(String)
    plant_type: Mapped[str] = mapped_column(String)  # one of PLANT_TYPES

    bus_id: Mapped[int | None] = mapped_column(ForeignKey("bus.id"), default=None)
    downstream_gen_plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant.id"), default=None)
    downstream_vert_plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant.id"), default=None)

    cos_var: Mapped[float] = mapped_column(Float, default=0.0)  # CenCosVar
    rendimiento: Mapped[float] = mapped_column(Float, default=0.0)  # CenRen
    pot_min: Mapped[float] = mapped_column(Float, default=0.0)
    pot_max: Mapped[float] = mapped_column(Float, default=0.0)
    vert_min: Mapped[float | None] = mapped_column(Float, default=None)  # Embalse/Serie only
    vert_max: Mapped[float | None] = mapped_column(Float, default=None)
    cau_afl: Mapped[float | None] = mapped_column(Float, default=None)  # Embalse/Serie/Pasada only —
    # the flat/default inflow assumed before any plpaflce.dat per-block override.
    estoc_findep: Mapped[bool | None] = mapped_column(Boolean, default=None)  # Embalse/Serie/Pasada only

    # Read by the solver but not retained (see class docstring) — kept for file fidelity only.
    cen_ipot: Mapped[int] = mapped_column(Integer, default=1)
    min_tec: Mapped[bool] = mapped_column(Boolean, default=False)
    inter: Mapped[bool] = mapped_column(Boolean, default=False)
    fcad: Mapped[bool] = mapped_column(Boolean, default=False)
    mttd_hrz: Mapped[bool] = mapped_column(Boolean, default=False)
    p_ini: Mapped[float] = mapped_column(Float, default=0.0)
    cost_arranque: Mapped[float] = mapped_column(Float, default=0.0)
    cost_detencion: Mapped[float] = mapped_column(Float, default=0.0)
    on_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    case: Mapped[Case] = relationship()
    bus: Mapped[Bus | None] = relationship(foreign_keys=[bus_id])
    downstream_gen_plant: Mapped["Plant | None"] = relationship(
        foreign_keys=[downstream_gen_plant_id], remote_side=[id]
    )
    downstream_vert_plant: Mapped["Plant | None"] = relationship(
        foreign_keys=[downstream_vert_plant_id], remote_side=[id]
    )
    reservoir: Mapped["Reservoir | None"] = relationship(back_populates="plant", uselist=False)


class Reservoir(Base):
    """1:1 extension of an EMBALSE-type Plant — the fields plpcnfce.dat's Embalse block alone
    carries (line4's trailing 6 fields: EmbVolIni/Fin/Min/Max, EmbFEsc, EmbCFUE)."""

    __tablename__ = "reservoir"

    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"), primary_key=True)
    vol_ini: Mapped[float] = mapped_column(Float, default=0.0)
    vol_fin: Mapped[float] = mapped_column(Float, default=0.0)
    vol_min: Mapped[float] = mapped_column(Float, default=0.0)
    vol_max: Mapped[float] = mapped_column(Float, default=0.0)
    f_esc: Mapped[float] = mapped_column(Float, default=1.0)  # no confirmed Excel source (see Phase
    # 2 migration notes) — defaults to 1.0 unless bootstrapped from an existing golden file.
    cfue: Mapped[bool] = mapped_column(Boolean, default=False)

    plant: Mapped[Plant] = relationship(back_populates="reservoir")


class ReservoirYieldCurve(Base):
    """plpcenre.dat record. No confirmed Excel/VBA source was found for this file at all (searched
    both xla workbooks) — likely hand-maintained hydraulic engineering data. Bootstrapped from the
    case's existing golden file; see db/migrate_from_xlsm.py."""

    __tablename__ = "reservoir_yield_curve"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))  # "Nombre de Central"
    reservoir_plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))  # "Nombre del Embalse"
    avg_yield: Mapped[float] = mapped_column(Float)  # Rendimiento Medio

    plant: Mapped[Plant] = relationship(foreign_keys=[plant_id])
    reservoir_plant: Mapped[Plant] = relationship(foreign_keys=[reservoir_plant_id])
    segments: Mapped[list["ReservoirYieldSegment"]] = relationship(
        back_populates="curve", cascade="all, delete-orphan", order_by="ReservoirYieldSegment.ind"
    )


class ReservoirYieldSegment(Base):
    __tablename__ = "reservoir_yield_segment"

    id: Mapped[int] = mapped_column(primary_key=True)
    curve_id: Mapped[int] = mapped_column(ForeignKey("reservoir_yield_curve.id"))
    ind: Mapped[int] = mapped_column(Integer)
    volume: Mapped[float] = mapped_column(Float)
    slope: Mapped[float] = mapped_column(Float)
    constant: Mapped[float] = mapped_column(Float)
    scale: Mapped[float] = mapped_column(Float, default=1.0)

    curve: Mapped[ReservoirYieldCurve] = relationship(back_populates="segments")


class ReservoirPmaxCurve(Base):
    """plpcenpmax.dat record. Same no-Excel-source situation as ReservoirYieldCurve above."""

    __tablename__ = "reservoir_pmax_curve"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    reservoir_plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))

    plant: Mapped[Plant] = relationship(foreign_keys=[plant_id])
    reservoir_plant: Mapped[Plant] = relationship(foreign_keys=[reservoir_plant_id])
    segments: Mapped[list["ReservoirPmaxSegment"]] = relationship(
        back_populates="curve", cascade="all, delete-orphan", order_by="ReservoirPmaxSegment.id"
    )


class ReservoirPmaxSegment(Base):
    __tablename__ = "reservoir_pmax_segment"

    id: Mapped[int] = mapped_column(primary_key=True)
    curve_id: Mapped[int] = mapped_column(ForeignKey("reservoir_pmax_curve.id"))
    volume: Mapped[float] = mapped_column(Float)
    slope: Mapped[float] = mapped_column(Float)
    constant: Mapped[float] = mapped_column(Float)

    curve: Mapped[ReservoirPmaxCurve] = relationship(back_populates="segments")


class Battery(Base):
    """plpcenbat.dat record — the detailed battery config (injectors, capacity). Distinct from the
    generic BATERIA-type Plant row in plpcnfce.dat, which only carries that file's generic fields;
    `plant_id` links the two by name at import time."""

    __tablename__ = "battery"
    __table_args__ = (UniqueConstraint("case_id", "bat_ind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    bat_ind: Mapped[int] = mapped_column(Integer)  # Baterias sheet's own INDICE numbering
    bus_id: Mapped[int] = mapped_column(ForeignKey("bus.id"))
    discharge_loss_factor: Mapped[float] = mapped_column(Float)  # FPD, "Rendimiento de Descarga"
    capacity_min: Mapped[float] = mapped_column(Float)
    capacity_max: Mapped[float] = mapped_column(Float)

    plant: Mapped[Plant] = relationship()
    bus: Mapped[Bus] = relationship()
    injectors: Mapped[list["BatteryInjector"]] = relationship(
        back_populates="battery", cascade="all, delete-orphan", order_by="BatteryInjector.id"
    )


class BatteryInjector(Base):
    """A charging-load plant feeding into a battery (NIny records per battery; this case has
    exactly one per battery, but the format and this schema both support more)."""

    __tablename__ = "battery_injector"

    id: Mapped[int] = mapped_column(primary_key=True)
    battery_id: Mapped[int] = mapped_column(ForeignKey("battery.id"))
    name: Mapped[str] = mapped_column(String)  # e.g. 'BAT_ARENALES_LOAD' — a pseudo-plant name, not
    # necessarily a real row in `plant`.
    loss_factor: Mapped[float] = mapped_column(Float)  # FPC, "Rendimiento de Carga"

    battery: Mapped[Battery] = relationship(back_populates="injectors")


# =================================================================================================
# Phase 3 — demand & thermal costs
# =================================================================================================
#
# The demand pipeline replicates Rutina04.DEMxBarra2 (normalized per-bus/hour load shape x weekly
# system-wide GWh target -> scaled per-bus demand) plus Archivo_03_PLPDEM_5A's block aggregation —
# see demand_calc.py for the actual algorithm and the plan/session notes for how this was traced
# out of the VBA source (this is a fully-specified algorithm, not a bootstrap-from-golden-file
# situation like several Phase 1/2 fields).

DEMAND_CATEGORIES = ("R", "L", "LD")  # Residencial, Libre, Libre en Distribucion
DAY_TYPES = (1, 2, 3, 4)  # 1=Domingo, 2=Lunes, 3=Sabado, 4=Trabajo(Tue-Fri) — VBA's own encoding


class DemandProfile(Base):
    """One normalized historical hourly load value from the Demanda-R/L/LD sheets: MW for one
    (bus, category, month, day-type, hour). ~480k rows for this case (139 buses x 3 categories x
    12 months x 4 day-types x 24 hours) — bulk-inserted at import time, not built via the ORM one
    row at a time (see migrate_from_xlsm._import_demand_profiles)."""

    __tablename__ = "demand_profile"
    __table_args__ = (
        UniqueConstraint("case_id", "bus_id", "category", "month", "day_type", "hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    bus_id: Mapped[int] = mapped_column(ForeignKey("bus.id"))
    category: Mapped[str] = mapped_column(String)  # one of DEMAND_CATEGORIES
    month: Mapped[int] = mapped_column(Integer)  # 1-12
    day_type: Mapped[int] = mapped_column(Integer)  # one of DAY_TYPES
    hour: Mapped[int] = mapped_column(Integer)  # 1-24
    mw: Mapped[float] = mapped_column(Float)


class ConsumptionWeek(Base):
    """One row of the Consumo sheet: a week's forecast system-wide consumption per category, used
    to rescale DemandProfile's normalized shape to real energy targets (DemFC in DEMxBarra2)."""

    __tablename__ = "consumption_week"
    __table_args__ = (UniqueConstraint("case_id", "week_num"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    week_num: Mapped[int] = mapped_column(Integer)  # 1-based, in sheet row order
    start_date: Mapped[_date] = mapped_column(Date)
    num_days: Mapped[int] = mapped_column(Integer)
    gwh_r: Mapped[float] = mapped_column(Float)
    gwh_l: Mapped[float] = mapped_column(Float)
    gwh_ld: Mapped[float] = mapped_column(Float)


class Holiday(Base):
    """A single holiday date (Consumo sheet's 'Festivos' column) — reclassifies that calendar day
    as day-type 1 (Domingo) regardless of its actual weekday, matching DEMxBarra2 exactly."""

    __tablename__ = "holiday"
    __table_args__ = (UniqueConstraint("case_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    date: Mapped[_date] = mapped_column(Date)


class IndustrialProject(Base):
    """Proyectos sheet: a fixed MW demand addition at one bus over a date range."""

    __tablename__ = "industrial_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    bus_id: Mapped[int] = mapped_column(ForeignKey("bus.id"))
    start_date: Mapped[_date] = mapped_column(Date)
    end_date: Mapped[_date] = mapped_column(Date)
    demand_mw: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String, default=None)

    bus: Mapped[Bus] = relationship()


class ThermalCostSchedule(Base):
    """plpcosce.dat source record, from CV_MP sheet columns G-J (CENTRAL/INICIAL/FINAL/[US$/MWh])
    — a contiguous stage range sharing one cost, expanded into per-stage rows at generation time.
    Note: CV_MP also has an earlier, unrelated NAME/DATE1/DATE2/CV table (columns B-E) that turned
    out NOT to be this file's source — see migrate_from_xlsm.py's docstring for how that was ruled
    out (the G-J table's per-central row count matches plpcnfce.dat's NCenCos exactly; the B-E
    table doesn't)."""

    __tablename__ = "thermal_cost_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    stage_start: Mapped[int] = mapped_column(Integer)  # num_eta, inclusive
    stage_end: Mapped[int] = mapped_column(Integer)  # num_eta, inclusive
    cost_var: Mapped[float] = mapped_column(Float)

    plant: Mapped[Plant] = relationship()


# =================================================================================================
# Phase 4 — maintenance schedules
# =================================================================================================
#
# Unlike plpcosce.dat's CV_MP source, three of these four Excel-sourced tables come PRE-MERGED
# into block/stage ranges (a second table on the same sheet, to the right of the raw date-range
# input table) — no date->stage conversion logic needed for them at all. Only ReservoirMinVolume
# Slack (MantEMBh) has just the raw date-range table and needs date->block/stage conversion (see
# migrate_from_xlsm.py's _date_range_to_stage_range) plus the ported Vol_<Name> curves (level ->
# volume). Battery maintenance (plpmanbat.dat, per the user's 2026-08-30 ruling: the code's
# filename is the rule, not the checked-in sample's "plpmantbat.dat") has no Excel source at all
# (confirmed: no maintenance columns/sheet found for Baterias) — bootstrapped from the golden file,
# same mechanism as Phase 2's reservoir curves.


class PlantMaintenance(Base):
    """plpmance.dat source: MantCEN sheet's pre-merged block-range table (columns I-M:
    CENTRAL/INICIAL/FINAL/MÍNIMA/MÁXIMA, block-numbered — confirmed against the case's own data:
    max FINAL there is 234, this case's total block count). Ranges need not cover every block for
    a plant, and multiple ranges per plant are normal (~238k populated sheet rows across ~2783
    plants) — expanded into one row per block at generation time, same pattern as
    ThermalCostSchedule."""

    __tablename__ = "plant_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    block_start: Mapped[int] = mapped_column(Integer)  # num_blo, inclusive
    block_end: Mapped[int] = mapped_column(Integer)  # num_blo, inclusive
    pot_min: Mapped[float] = mapped_column(Float)
    pot_max: Mapped[float] = mapped_column(Float)

    plant: Mapped[Plant] = relationship()


class LineMaintenance(Base):
    """plpmanli.dat source: MantLIN sheet's pre-merged block-range table (columns I-N)."""

    __tablename__ = "line_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    line_id: Mapped[int] = mapped_column(ForeignKey("line.id"))
    block_start: Mapped[int] = mapped_column(Integer)
    block_end: Mapped[int] = mapped_column(Integer)
    capacity_ab: Mapped[float] = mapped_column(Float)
    capacity_ba: Mapped[float] = mapped_column(Float)
    operational: Mapped[bool] = mapped_column(Boolean)

    line: Mapped[Line] = relationship()


class ReservoirMaintenance(Base):
    """plpmanem.dat source: MantEMB sheet's pre-merged stage-range table (columns H-L) — already
    volume-valued (not level/cota), unlike MantEMBh below."""

    __tablename__ = "reservoir_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))  # the Embalse-type plant
    stage_start: Mapped[int] = mapped_column(Integer)  # num_eta, inclusive
    stage_end: Mapped[int] = mapped_column(Integer)  # num_eta, inclusive
    vol_min: Mapped[float] = mapped_column(Float)
    vol_max: Mapped[float] = mapped_column(Float)

    plant: Mapped[Plant] = relationship()


class ReservoirMinVolumeSlack(Base):
    """plpminembh.dat source: MantEMBh sheet — level (Cota)/cost by date range, the one Phase 4
    table with no pre-merged stage-range companion. `level_min` is stored in the sheet's own units
    (m.s.n.m.) — converted to volume via curves/reservoir_volume.py at generation time, same
    raw-units-in-DB / converted-at-generation approach as Phase 2's Reservoir.vol_*."""

    __tablename__ = "reservoir_min_volume_slack"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    stage_start: Mapped[int] = mapped_column(Integer)
    stage_end: Mapped[int] = mapped_column(Integer)
    level_min: Mapped[float] = mapped_column(Float)  # Cota, m.s.n.m.
    cost: Mapped[float] = mapped_column(Float)

    plant: Mapped[Plant] = relationship()


class BatteryMaintenance(Base):
    """plpmanbat.dat source — no Excel source at all (see module docstring); bootstrapped from
    the golden file. Block-range table, analogous to PlantMaintenance."""

    __tablename__ = "battery_maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    battery_id: Mapped[int] = mapped_column(ForeignKey("battery.id"))
    block_start: Mapped[int] = mapped_column(Integer)
    block_end: Mapped[int] = mapped_column(Integer)
    e_min: Mapped[float] = mapped_column(Float)  # negative sentinel = "no override", see spec
    e_max: Mapped[float] = mapped_column(Float)

    battery: Mapped[Battery] = relationship()


# =================================================================================================
# Phase 5 — hydrology & inflows
# =================================================================================================
#
# All four tables here are bootstrapped from the golden .dat files rather than derived from the
# Caudales_Ah1/Ah2/Caudales_historicos or Hidrología sheets — per the plan's own scoping, not a
# shortcut discovered along the way: the "ALEATORIA" hydrology-scenario sampling in Rutina04's
# sibling logic (Archivo_07/12/13) depends on VBA's own `Rnd` PRNG, which cannot be reproduced
# bit-for-bit in Python. These are plain editable data going forward (and a future re-sampling
# utility can regenerate them using Python's own `random`, explicitly not bit-compatible with old
# VBA runs — that's fine, these are stochastic scenario draws, not something needing historical
# reproducibility). Multi-value fields (a hydrology-class vector, an aperture-index list) are
# stored as JSON rather than one row per value — these are always read/written as one unit, and
# normalizing further would multiply row counts a hundredfold for no relational benefit.


class Inflow(Base):
    """plpaflce.dat source — one row per (plant, block), holding all NClase hydrology-class
    inflow values as a JSON list (index 0 = hydrology class 1, etc.)."""

    __tablename__ = "inflow"
    __table_args__ = (UniqueConstraint("case_id", "plant_id", "num_blo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plant.id"))
    num_blo: Mapped[int] = mapped_column(Integer)
    values: Mapped[list[float]] = mapped_column(JSON)  # length == case's n_clase

    plant: Mapped[Plant] = relationship()


class HydrologyScenarioAssignment(Base):
    """plpidsim.dat source — one row per stage, holding the hydrology-class assigned to each of
    the case's NSimul simulation slots as a JSON list (index 0 = simulation 1, etc.)."""

    __tablename__ = "hydrology_scenario_assignment"
    __table_args__ = (UniqueConstraint("case_id", "stage_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("stage.id"))
    hydro_class_by_sim: Mapped[list[int]] = mapped_column(JSON)  # length == case's n_simul

    stage: Mapped[Stage] = relationship()


class ApertureIndexSimulation(Base):
    """plpidape.dat source — one row per (simulation, stage), holding that stage's aperture-index
    list as JSON (variable length per row — see spec). Stage 1 is excluded (the file format itself
    restricts Etapa to 2..NEtapa)."""

    __tablename__ = "aperture_index_simulation"
    __table_args__ = (UniqueConstraint("case_id", "simulation_slot", "stage_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    simulation_slot: Mapped[int] = mapped_column(Integer)  # 1..n_simul
    stage_id: Mapped[int] = mapped_column(ForeignKey("stage.id"))
    apertures: Mapped[list[int]] = mapped_column(JSON)

    stage: Mapped[Stage] = relationship()


class ApertureIndexAggregate(Base):
    """plpidap2.dat source — one row per stage (simulation-independent aggregate table; see
    spec's distinction from ApertureIndexSimulation). Stage 1 excluded, same as above."""

    __tablename__ = "aperture_index_aggregate"
    __table_args__ = (UniqueConstraint("case_id", "stage_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case.id"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("stage.id"))
    apertures: Mapped[list[int]] = mapped_column(JSON)

    stage: Mapped[Stage] = relationship()
