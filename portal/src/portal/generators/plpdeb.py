"""plpdeb.dat — solver debug/logging flags (one row per case). See scratchpad spec:
static_formats.md#plpdeb.dat."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.models import DebugParams
from .common import DatWriter, logical


def generate(session: Session, case_id: int) -> str:
    p = session.get(DebugParams, case_id)
    w = DatWriter()
    w.comment("Archivo con parametros de Debug (pcpdeb.dat)")
    w.comment("FLogFile")
    w.fields(logical(p.f_log))
    w.comment("PriProgDin PDSvFl PMSvFl FDatChe ErSvFl PsFzFl FTSvFl FSvLaPs")
    w.fields(
        logical(p.pri_prog_din),
        logical(p.pd_sv_fl),
        logical(p.pm_sv_fl),
        logical(p.f_dat_che),
        logical(p.er_sv_fl),
        logical(p.ps_fz_fl),
        logical(p.ft_sv_fl),
        logical(p.f_sv_la_ps),
    )
    w.comment("IndSimImp, IndIteImp, FBest, IndEta1Imp, IndEta2Imp")
    w.fields(
        f"{p.ind_sim_imp:02d}",
        f"{p.ind_ite_imp:02d}",
        logical(p.f_best),
        p.ind_eta1_imp,
        p.ind_eta2_imp,
    )
    return w.render()
