"""Orchestration: runs the deterministic modules in order and returns results (partial if inputs are missing)."""
from . import db
from .i18n import L
from .engines import geometry as G, environment as E, materials as M, construction as C, pattern as P, nesting as N, sewing as S, validation as V
from .engines.sewing_base import seam_spec


def run(project):
    res = {}
    robot, env, reqs = project.get("robot", {}), project.get("environment", {}), {**db.default_requirements(), **project.get("requirements", {})}
    segs, errs = G.normalize_segments(robot.get("segments"))
    res["geometry"] = dict(errors=errs)
    if errs:
        res["stage"] = "geometry"
        return res
    js = G.joint_summary(segs)
    clearance = G.sweep_clearance(segs)
    res["geometry"].update(segments=segs, joints=js, clearance=clearance, envelope=G.total_envelope(segs))
    comp = E.completeness(env, robot)
    res["environment"] = dict(completeness=comp)
    if comp["missing"]:
        res["stage"] = "environment"
        return res
    pack = E.derive_requirements(env, reqs, js)
    res["environment"]["pack"] = pack
    mats = db.catalog("materials")
    sel = M.select(mats, pack, reqs, segs)
    res["material"] = sel
    rec = sel["recommended"]
    mat = db.catalog_get("materials", rec["id"])
    if rec["effective"]["gsm_confirmed"] is False and reqs.get("confirmed"):
        pass
    eff = rec["effective"]
    seam = seam_spec(mat, pack, eff, reqs)
    plan = C.design(segs, reqs, mat, eff, seam, js["per_joint"])
    plan["seam"], plan["segs"] = seam, segs
    res["construction"] = plan
    if plan["errors"] and not plan["sections"]:
        res["stage"] = "construction"
        return res
    built = P.build(plan, segs, eff, seam, reqs, mat, pack)
    res["pattern"] = built
    nres = N.nest(built["pieces"], float(reqs["roll_width_mm"]), bool(reqs.get("allow_rotate_90")))
    calc = N.consumption(built["pieces"], nres, reqs, eff, mat)
    res["nesting"] = nres
    res["consumption"] = calc
    liner_calc = None
    if int(reqs.get("layers") or 1) == 2:
        liner = next((m for m in mats if m.get("role") == "liner"), None)
        lp = [p for p in built["pieces"] if p["kind"] != "patch"]
        ln = N.nest(lp, float(reqs["roll_width_mm"]), False)
        liner_calc = N.consumption(lp, ln, reqs, dict(eff, shrink_confirmed=True), liner or {})
        res["liner"] = dict(material=liner, consumption=liner_calc)
    thr = S.select_thread(mat, pack, eff, db.catalog("threads"))
    stitch = S.stitch_spec(mat, pack, eff, seam)
    mach = S.select_machine(db.catalog("machines"), mat, pack, eff, built["seams"], plan, stitch, thr, reqs)
    accs = db.catalog("accessories")
    sel_acc = {c: S.select_accessory(accs, c, pack, mat) for c in ("zipper", "hook_loop", "snap", "buckle", "webbing", "binding", "elastic", "seam_tape", "gasket")}
    if seam.get("seal"):
        want = dict(seam_tape_hotair="tape_tpu", rtv="sealant_rtv", ptfe_tape="tape_ptfe").get(seam["seal"]["method"])
        a = next((x for x in accs if x["id"] == want), None)
        if a:
            sel_acc["seam_tape"] = dict(item=a, meets_all=True, fails=[], unknown=0)
    used = set()
    if built["zippers"]: used.add("zipper")
    if built["velcro"]: used.add("hook_loop")
    if built["snaps"]: used.add("snap")
    used.add("elastic" if reqs.get("elastic") else "webbing")
    if not reqs.get("elastic"): used.add("buckle")
    if built["bindings"]: used.add("binding")
    if seam.get("seal"): used.add("seam_tape")
    if pack.get("waterproof_level", 0) >= 3 and built["zippers"]: used.add("gasket")
    sel_acc = {k: (v if k in used else None) for k, v in sel_acc.items()}
    res["sewing"] = dict(thread=thr, stitch=stitch, machine=mach, accessories=sel_acc, seam=seam)
    items = S.bom(project["id"], mat, eff, calc, liner_calc, thr, stitch, plan, built, sel_acc, mach, seam, reqs, pack)
    res["bom"] = items
    ctx = dict(segs=segs, pack=pack, rec=rec, plan=plan, built=built, calc=calc, thr=thr, mach=mach, stitch=stitch,
               accs=sel_acc, reqs=reqs, eff=eff, clearance=clearance)
    checks = V.validate(ctx)
    res["validation"] = dict(checks=checks, summary=V.summary(checks))
    res["stage"] = "complete"
    return res
