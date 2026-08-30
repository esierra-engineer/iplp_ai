"""plpmat.dat — solver math parameters (one row per case). See scratchpad spec:
static_formats.md#plpmat.dat."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..db.models import MathParams
from .common import DatWriter, logical, number


def generate(session: Session, case_id: int) -> str:
    p = session.get(MathParams, case_id)
    w = DatWriter()
    w.comment("Archivo con Parametros Matematicos (plpmat.dat)")
    w.comment("PDMaxIte    PDError UmbIntConf NPlanosPorDefecto")
    w.fields(p.pd_max_iter, number(p.pd_error, 3), number(p.umb_int_conf, 3))
    w.comment("PMMaxIte    PMError")
    w.fields(p.pm_max_iter, number(p.pm_error, 1))
    w.comment("Lambda CTasa CCauFal  CVert CInter Ctransm FCotFinEF FPreProc FPrevia")
    w.fields(
        number(p.lambda_, 2),
        number(p.c_tasa, 1),
        number(p.c_caudal_falla, 1),
        number(p.c_vertimiento, 2),
        number(p.c_inter, 2),
        number(p.c_transmision, 2),
        logical(p.f_vol_fin_emb),
        logical(p.f_pre_proc),
        logical(p.f_previa),
    )
    w.comment("FFixTrasm  FSeparaFCF  FGrabaCSV   FGrabaRES")
    w.fields(
        logical(p.f_fix_trasm), logical(p.f_separa_fcf), logical(p.f_graba_csv), logical(p.f_graba_res)
    )
    w.comment("ABLMax    ABEpsilon NumEtaCF")
    w.fields(p.ab_max, number(p.ab_epsilon, 3), p.num_eta_cf)
    w.comment("FConvPGradx  FConvPVar  UmbGradX  UmbZSPF")
    w.fields(
        logical(p.f_conv_pgradx), logical(p.f_conv_pvar), number(p.umb_gradx, 1), number(p.umb_zspf, 1)
    )
    return w.render()
