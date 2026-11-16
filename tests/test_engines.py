import copy, math, os, tempfile
os.environ["RCD_DATA_DIR"] = tempfile.mkdtemp()
import pytest
from rcd import pipeline, example, db
from rcd.engines import geometry as G, nesting as N, construction as C, environment as E, materials as M, validation as V


def proj(**over):
    p = copy.deepcopy(example.EXAMPLE); p["id"] = "t"
    for k, v in over.items():
        p[k] = v
    return p


def test_pipeline_complete_and_no_green_material_without_verified_data():
    r = pipeline.run(proj())
    assert r["stage"] == "complete"
    st = {c["id"]: c["status"] for c in r["validation"]["checks"]}
    assert st["material_env"] != "green"          # catalogue data are 'typical'
    assert st["pattern_dims"] == "green"


def test_cylinder_circumference_formula():
    segs, _ = G.normalize_segments([{"shape": "cylinder", "length": 100, "d1": 200}])
    assert G.circumference(segs[0], 0.5) == pytest.approx(math.pi * (200 + 20 + 0.5))


def test_pattern_rect_equals_finished_plus_allowances():
    r = pipeline.run(proj())
    for p in r["pattern"]["pieces"]:
        if p["finished"]["shape"] == "rect":
            f, a = p["finished"], p["allowances"]
            assert p["bbox"][0] == pytest.approx(f["width"] + a["left"] + a["right"])
            assert p["bbox"][1] == pytest.approx(f["length"] + a["start"] + a["end"])


def test_frustum_development_area_matches_cone_lateral_area():
    p = proj(); r = pipeline.run(p)
    fr = next(x for x in r["pattern"]["pieces"] if x["kind"] == "frustum")
    f = fr["finished"]
    area_sector = 0.5 * math.radians(f["angle_deg"]) * (f["R_outer"] ** 2 - f["R_inner"] ** 2)
    s = f["R_outer"] - f["R_inner"]
    # lateral area of frustum = pi (r1 + r2) s ; r from arc lengths
    r_big, r_small = f["arc_outer"] / (2 * math.pi), f["arc_inner"] / (2 * math.pi)
    assert area_sector == pytest.approx(math.pi * (r_big + r_small) * s, rel=1e-6)


def test_bellows_pleats_absorb_required_compression():
    b = C.bellows_design(delta=100.0, t=0.5, h=20.0)
    assert b["capacity"] >= 2 * 100.0 - 1e-6
    assert b["n"] * 2 * b["h"] <= 0.9 * b["Ld"] + 1e-6
    assert b["min_len"] <= b["Lj"] - 100.0 + 1e-6


def test_nesting_has_no_overlaps_and_fits_width():
    r = pipeline.run(proj()); nes = r["nesting"]
    pl = nes["placements"]
    for p in pl:
        assert p["x"] >= 15 - 1e-6 and p["x"] + p["w"] <= 1500 - 15 + 1e-6
    for i, a in enumerate(pl):
        for b in pl[i + 1:]:
            sep = a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]
            assert sep, (a["id"], b["id"])
    c = r["consumption"]
    assert c["buy_m"] >= c["marker_length_m"]
    assert 0 < c["waste_pct"] < 100


def test_wide_piece_is_split_into_panels_to_fit_roll():
    p = proj(); p["robot"]["segments"][0]["d1"] = 700   # circumference ~2.2 m > 1.5 m roll
    r = pipeline.run(p)
    base = [x for x in r["pattern"]["pieces"] if x["section"] == "S1" and x["kind"] == "tube"]
    assert len(base) >= 2 and all(x["bbox"][0] <= 1470 + 1e-6 for x in base)


def test_missing_dimensions_do_not_get_invented():
    p = proj(); p["robot"]["segments"][1]["length"] = None
    r = pipeline.run(p)
    assert r["stage"] == "geometry" and r["geometry"]["errors"]


def test_missing_temperatures_block_material_selection():
    p = proj(); p["environment"]["tmax_c"] = None
    assert pipeline.run(p)["stage"] == "environment"


def test_unknown_factor_is_not_treated_as_absent():
    env = {"tmin_c": 0, "tmax_c": 30, "factors": {}}
    comp = E.completeness(env)
    assert comp["questions"] and E.derive_requirements(env, db.default_requirements())["critical_unresolved"]


def test_continuous_cutting_oil_excludes_pvc_and_spark_excludes_pvc():
    env = {"tmin_c": 5, "tmax_c": 40, "cycles_per_day": 100, "factors": {"oil_cutting": {"state": "present", "level": 3}, "spatter": {"state": "present", "level": 2}}}
    pack = E.derive_requirements(env, db.default_requirements())
    res = M.select(db.catalog("materials"), pack, {})
    assert res["recommended"]["id"] not in ("pvc_pes", "pu_pes")
    assert any(x["id"] == "pvc_pes" and not x["meets_all"] for x in res["rejected"])


def test_no_material_meets_all_is_reported_not_hidden():
    env = {"tmin_c": 5, "tmax_c": 600, "factors": {"oil_cutting": {"state": "present", "level": 3}}}
    res = M.select(db.catalog("materials"), E.derive_requirements(env, db.default_requirements()), {})
    assert not res["recommended"]["meets_all"] and res["warnings"]


def test_glass_fabric_excluded_when_bellows_required():
    segs, _ = G.normalize_segments(example.EXAMPLE["robot"]["segments"])
    js = G.joint_summary(segs); assert js["needs_bellows"]
    env = {"tmin_c": 5, "tmax_c": 40, "factors": {"waterproof": {"state": "present", "level": 1}}}
    res = M.select(db.catalog("materials"), E.derive_requirements(env, db.default_requirements(), js), {})
    assert not res["recommended"]["crease_sensitive"]


def test_collision_detected_when_arm_folds_into_base():
    p = proj(); p["robot"]["segments"][2]["joint_after"] = dict(type="bend", axis=3, min=-170, max=170)
    r = pipeline.run(p)
    assert r["geometry"]["clearance"]["gap"] < 0
    st = {c["id"]: c["status"] for c in r["validation"]["checks"]}
    assert st["clearance"] == "red" and not r["validation"]["summary"]["can_approve"]


def test_removable_without_closure_is_red():
    p = proj(); p["requirements"].update(zipper=False, velcro=False, snaps=False)
    r = pipeline.run(p)
    assert {c["id"]: c["status"] for c in r["validation"]["checks"]}["removable"] == "red"


def test_hot_surface_above_material_limit_is_red():
    p = proj(); p["robot"]["segments"][0]["hot_c"] = 400
    r = pipeline.run(p)
    assert any(c["id"] == "hot_surface" and c["status"] == "red" for c in r["validation"]["checks"]) or r["material"]["recommended"]["tmax_c"] >= 410


def test_thread_and_machine_selection_consistent():
    r = pipeline.run(proj()); s = r["sewing"]
    assert s["machine"]["machine"]["max_thickness_mm"] >= s["machine"]["required_thickness_mm"] * 1.2
    assert s["machine"]["machine"]["max_tex"] >= s["thread"]["tex"]


def test_bom_has_fabric_thread_needles_and_positive_quantities():
    r = pipeline.run(proj())
    cats = {b["category"] for b in r["bom"]}
    assert {"fabric", "thread", "needle"} <= cats
    assert all(b["qty"] is None or b["qty"] > 0 for b in r["bom"])


def test_shrinkage_scales_cut_pattern():
    a = pipeline.run(proj())
    p = proj(); p["requirements"]["confirmed"] = {"shrink_warp_pct": 2, "shrink_weft_pct": 1}
    b = pipeline.run(p)
    pa, pb = a["pattern"]["pieces"][0], b["pattern"]["pieces"][0]
    assert pb["bbox"][0] == pytest.approx(pa["bbox"][0] * 1.01) and pb["bbox"][1] == pytest.approx(pa["bbox"][1] * 1.02)


def test_two_layers_adds_liner_calculation():
    p = proj(); p["requirements"]["layers"] = 2
    r = pipeline.run(p)
    assert r["liner"]["consumption"]["ok"] and any("felt" in b["name"]["en"].lower() for b in r["bom"])
