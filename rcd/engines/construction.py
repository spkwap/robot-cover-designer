"""Cover construction module: decides sections, modules, joins, bellows, closures and records the technical rationale."""
import math
from ..i18n import L
from . import geometry as G
from .sewing_base import OVERLAP_LEN


def _ceil5(x):
    return math.ceil(x / 5.0) * 5.0


def bellows_design(delta, t, h, user_len=None):
    """Pleat count and joint length. Developed length Ld = Lj + delta (outer edge at full bend); compressed length at the
    inner edge = Lj - delta; each pleat of height h consumes 2h of fabric and removes (2h - 2t) of length when folded."""
    cap = 2 * h - 2 * t
    n = math.ceil(2 * delta / cap)
    Lj = max(user_len or 0, _ceil5(1.5 * delta), 80.0)
    while n * 2 * h > 0.9 * (Lj + delta):
        Lj += 5.0
    Ld = Lj + delta
    min_len = Ld - n * cap
    return dict(n=n, Lj=Lj, Ld=Ld, h=h, min_len=min_len, capacity=n * cap, delta=delta)


def design(segs, reqs, material, eff, seam, ji_all):
    t = eff["thickness_mm"]
    warn, rationale, errors = [], [], []
    modular = bool(reqs.get("modular", True))
    h = float(reqs.get("pleat_height_mm") or 20)
    removable = bool(reqs.get("removable", True))
    sections, joins = [], []
    cov_idx = [i for i, s in enumerate(segs) if s["cover"]]
    if not cov_idx:
        errors.append(dict(text=L("Żaden segment nie jest oznaczony do osłonięcia.", "No segment is marked for covering.")))
        return dict(sections=[], modules=[], joins=[], rationale=[], warnings=[], errors=errors, style="none")

    def sec(**k):
        k["id"] = f"S{len(sections) + 1}"
        sections.append(k)
        return k

    prev = None
    for i in cov_idx:
        s = segs[i]
        # was the previous segment adjacent & covered?
        adj = prev is not None and prev["seg"] == i - 1
        join_type = None
        if adj:
            jt = segs[i - 1]["joint_after"]["type"]
            if jt == "bend" and ji_all.get(i - 1, {}).get("needs_bellows"):
                join_type = "bellows"
            elif jt == "twist":
                join_type = "twist"
            else:
                join_type = "rigid"
        # bellows before this segment?
        bell_before = None
        if join_type == "bellows":
            ji = ji_all[i - 1]
            bell_before = bellows_design(ji["delta"], t, h, segs[i - 1]["joint_after"].get("cover_len"))
            if bell_before["Lj"] / 2 >= segs[i - 1]["length"] or bell_before["Lj"] / 2 >= s["length"]:
                warn.append(L(f"Sekcja harmonijkowa na przegubie za '{segs[i - 1]['name']}' jest dłuższa niż połowa sąsiedniego segmentu — zwiększ długość segmentów lub zmniejsz zakres ruchu.",
                              f"Bellows at the joint after '{segs[i - 1]['name']}' is longer than half of an adjacent segment - increase segment length or reduce range."))
        if bell_before:
            sec(kind="bellows", seg=i - 1, seg2=i, name=f"{segs[i - 1]['name']}→{s['name']}", finished_length=bell_before["Lj"], dev_length=bell_before["Ld"],
                bellows=bell_before, join_in=prev["id"] if prev else None, joint_type="bellows")
            sections[-1]["prev_join"] = "bellows"
        # tube section for the segment
        start_cut = (bell_before["Lj"] / 2) if bell_before else 0.0
        # does a bellows follow?
        bell_after = None
        if i in ji_all and ji_all[i]["needs_bellows"] and (i + 1) in cov_idx:
            bell_after = bellows_design(ji_all[i]["delta"], t, h, s["joint_after"].get("cover_len"))
        end_cut = (bell_after["Lj"] / 2) if bell_after else 0.0
        Lf = s["length"] - start_cut - end_cut
        if Lf <= 5:
            errors.append(dict(seg=s["id"], text=L(f"Segment '{s['name']}': po odjęciu połowy długości sekcji harmonijkowych zostaje {Lf:.0f} mm — konstrukcja niemożliwa.",
                                                   f"Segment '{s['name']}': {Lf:.0f} mm left after bellows - construction impossible.")))
            Lf = max(Lf, 5.0)
        kind = {"cylinder": "tube", "frustum": "frustum", "box": "box"}[s["shape"]]
        ts = sec(kind=kind, seg=i, name=s["name"], finished_length=Lf, start_offset=start_cut, join_type=join_type if not bell_before else "bellows_in")
        prev = dict(seg=i, id=ts["id"])
        if bell_after:
            prev["bell_after"] = True

    # sequence of sections gives order; decide joins and modules
    modules, cur = [], None
    for k, sc in enumerate(sections):
        if k == 0:
            split = True
        else:
            pk = sections[k - 1]
            pk_last = pk["seg2"] if pk["kind"] == "bellows" else pk["seg"]
            diff = sc["seg"] - pk_last
            if diff not in (0, 1):
                reason = "gap"
            elif pk["kind"] == "bellows" or sc["kind"] == "bellows":
                reason = "bellows_join"
            elif segs[pk["seg"]]["joint_after"]["type"] == "twist":
                reason = "twist"
            else:
                reason = "rigid"
            split = reason in ("gap", "twist") or modular
            joins.append(dict(a=pk["id"], b=sc["id"], type="cuff" if split else "seam", reason=reason))
        if split:
            cur = dict(id=f"M{len(modules) + 1}", sections=[])
            modules.append(cur)
        cur["sections"].append(sc["id"])
        sc["module"] = cur["id"]
    if not modular and any(j["reason"] == "twist" for j in joins):
        rationale.append(L("Przeguby obrotowe (skręcne) wymuszają podział na moduły — ciągły pokrowiec jednoczęściowy ulegałby skręceniu i marszczeniu.",
                           "Rotary (twist) joints force a split into modules - a continuous one-piece cover would be twisted and wrinkled."))
    # module / section ends
    sec_by = {s["id"]: s for s in sections}
    for j in joins:
        a, b = sec_by[j["a"]], sec_by[j["b"]]
        if j["type"] == "cuff":
            a["end_finish"], b["start_finish"] = "hem", "skirt"
            b["skirt"] = OVERLAP_LEN
            j["overlap_mm"] = OVERLAP_LEN
        else:
            a["end_finish"], b["start_finish"] = "seam", "seam"
    for sc in sections:
        sc.setdefault("start_finish", "hem")
        sc.setdefault("end_finish", "hem")
        sc.setdefault("skirt", 0.0)
    # closures
    for sc in sections:
        mod_removable = removable
        if sc["kind"] == "bellows":
            sc["closure"] = "velcro" if reqs.get("velcro") else ("zipper" if reqs.get("zipper") else ("snaps" if reqs.get("snaps") else "none"))
            if sc["closure"] == "zipper":
                warn.append(L("Zamek w sekcji harmonijkowej: użyć zamka spiralnego o dużej elastyczności; zamki są wrażliwe na wielokrotne zginanie.",
                              "Zipper in a bellows section: use a flexible coil zipper; zippers are sensitive to repeated flexing."))
        else:
            sc["closure"] = ("zipper" if reqs.get("zipper") else "velcro" if reqs.get("velcro") else "snaps" if reqs.get("snaps") else
                             ("none" if mod_removable else "sewn"))
        if removable and sc["closure"] == "none":
            errors.append(dict(text=L("Pokrowiec ma być zdejmowany, a nie wybrano żadnego zapięcia (zamek/rzep/zatrzaski).",
                                      "Cover must be removable but no closure (zipper/velcro/snaps) was selected.")))
        if not removable and sc["closure"] in ("zipper", "velcro", "snaps"):
            pass
    # openings -> sections
    for si, s in enumerate(segs):
        for o in s.get("openings", []):
            pos = float(o.get("pos_mm") or 0)
            host = next((sc for sc in sections if sc["kind"] in ("tube", "frustum", "box") and sc["seg"] == si), None)
            if host is None:
                continue
            local = pos - host.get("start_offset", 0)
            if local < 20 or local > host["finished_length"] - 20:
                warn.append(L(f"Otwór '{o.get('name', '')}' w '{s['name']}' wypada poza strefą sekcji prostej (za blisko szwu/sekcji harmonijkowej).",
                              f"Opening '{o.get('name', '')}' in '{s['name']}' falls outside the straight section (too close to a seam/bellows)."))
                continue
            host.setdefault("openings", []).append(dict(o, local_pos=local))
    style = "bellows_segmented" if any(sc["kind"] == "bellows" for sc in sections) else "fitted_segmented" if len(modules) > 1 else "fitted"
    if any(sc["kind"] == "bellows" for sc in sections):
        rationale.append(L("Na przegubach zginanych zastosowano sekcje harmonijkowe: długość rozwinięta = długość nominalna + wydłużenie krawędzi zewnętrznej (δ = promień pokrowca × kąt), liczba plis dobrana tak, by przy maksymalnym zgięciu krawędź wewnętrzna zmieściła się w sprasowanych plisach.",
                           "Bellows sections are used on bending joints: developed length = nominal length + outer-edge elongation (delta = cover radius x angle); the number of pleats is chosen so the inner edge fits in the compressed pleats at maximum bend."))
    if modular:
        rationale.append(L("Konstrukcja modułowa: każdy moduł można zdjąć niezależnie (szybszy montaż/serwis); moduły łączy zakładka (skirt) 60 mm — moduł dalszy nakłada się na bliższy, mocowanie zapięciem/ściągaczem.",
                           "Modular design: each module can be removed independently (faster fitting/service); modules are joined with a 60 mm skirt overlap - the distal module overlaps the proximal one, secured by closure/cinch."))
    else:
        rationale.append(L("Konstrukcja ciągła: sekcje w obrębie modułu połączone szwem stałym; podział tylko tam, gdzie wymusza go kinematyka (przeguby obrotowe) lub przerwa w osłonie.",
                           "Continuous design: sections within a module are joined by permanent seams; split only where kinematics (rotary joints) or a gap in covering require it."))
    for s in segs:
        if s["cover"] and s.get("hot_c") is not None and s["hot_c"] >= 60:
            rationale.append(L(f"Segment '{s['name']}' ma gorącą powierzchnię ({s['hot_c']:g} °C): zwiększono luz promieniowy (szczelina powietrzna) do {G.ease_mm(s):g} mm.",
                               f"Segment '{s['name']}' has a hot surface ({s['hot_c']:g} C): radial clearance increased to {G.ease_mm(s):g} mm (air gap)."))
        if s["cover"] and s.get("cooling_vent"):
            warn.append(L(f"Segment '{s['name']}' wymaga chłodzenia: pokrowiec nie może zasłaniać wlotów/wylotów — oznaczono dodatkowy luz; zaplanuj otwory wentylacyjne lub strefę niezakrytą.",
                          f"Segment '{s['name']}' needs cooling: the cover must not block inlets/outlets - extra clearance applied; plan vent openings or leave the zone uncovered."))
    for s in segs:
        if not s["cover"]:
            rationale.append(L(f"Segment '{s['name']}' pozostawiony bez osłony (wybór użytkownika) — brak ochrony tej strefy.", f"Segment '{s['name']}' left uncovered (user choice) - this zone is not protected."))
    for mod in modules:
        mod["name"] = L(f"Moduł {mod['id'][1:]}: " + " + ".join(sec_by[x]["name"] for x in mod["sections"]), f"Module {mod['id'][1:]}: " + " + ".join(sec_by[x]["name"] for x in mod["sections"]))
    return dict(sections=sections, modules=modules, joins=joins, rationale=rationale, warnings=warn, errors=errors, style=style,
                modular=modular, parameters=dict(pleat_height=h, overlap_len=OVERLAP_LEN, thickness_used=t))
