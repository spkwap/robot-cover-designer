"""Seam specification (needed by construction + pattern before thread/machine selection)."""
import math
from ..i18n import L

ZIP_EDGE = 12.0
VELCRO_OVERLAP = 40.0
SNAP_OVERLAP = 35.0
CLOSURE_EDGE_FOLD = 15.0
OVERLAP_LEN = 60.0          # distal module skirt over proximal module (mm)
SELVEDGE = 15.0             # unusable edge per side (mm) - confirm with supplier
FLAP_W = 50.0


def seam_spec(material, pack, eff, reqs):
    t = eff["thickness_max_mm"]
    sa = 15.0 if t <= 0.8 else (20.0 if t <= 1.5 else 25.0)
    hem_fold = 20.0
    double = bool(material.get("fray"))
    hem = hem_fold * (2 if double else 1)
    if reqs.get("elastic"):
        hem = max(hem, 2 * 20.0)      # channel for a 6 mm cord
    seal = None
    if pack.get("waterproof_level", 0) >= 3 or pack.get("dust_need", 0) >= 3:
        fam = material["family"]
        if material.get("thermoplastic_coating"):
            seal = dict(method="seam_tape_hotair", text=L("taśma uszczelniająca na gorące powietrze (powłoka termoplastyczna)", "hot-air seam sealing tape (thermoplastic coating)"))
        elif "silicone" in fam:
            seal = dict(method="rtv", text=L("uszczelniacz silikonowy RTV na szwach", "silicone RTV sealant on seams"))
        elif "ptfe" in fam:
            seal = dict(method="ptfe_tape", text=L("taśma PTFE/FEP zgrzewana na gorąco", "heat-welded PTFE/FEP tape"))
        else:
            seal = dict(method="sealant", text=L("uszczelnienie szwów wg zaleceń dostawcy materiału", "seam sealing per material supplier's recommendation"))
    return dict(allowance=sa, hem=hem, hem_double_fold=double, hem_fold=hem_fold, rows=2, row_spacing=6.0, seal=seal,
                zip_edge=ZIP_EDGE, velcro_overlap=VELCRO_OVERLAP, snap_overlap=SNAP_OVERLAP, closure_fold=CLOSURE_EDGE_FOLD,
                overlap_len=OVERLAP_LEN, tolerance_mm=3.0)
