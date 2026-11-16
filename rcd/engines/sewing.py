"""Sewing technology module: thread, needle, stitch/seam, machine class and start settings, accessories, bill of materials."""
import math
from ..i18n import L
from . import geometry as G
from .environment import CHEM_LABEL

NEEDLE_BY_TEX = {40: (90, 100), 70: (110, 120), 90: (120, 130), 135: (140, 160), 210: (180, 200)}
UNCOATED = {"polyamide", "aramid", "aramid_felt"}


def _chem_needs(pack):
    return {r["key"]: r["need"] for r in pack["requirements"] if r["type"] == "chem"}


def _prop_need(pack, key):
    return max([r["need"] for r in pack["requirements"] if r["type"] == "prop" and r["key"] == key] or [0])


def select_thread(material, pack, eff, threads):
    cn = _chem_needs(pack)
    best = []
    for th in threads:
        fails, unknown, deficit = [], 0, 0
        for cls, need in cn.items():
            r = th["chem"].get(cls)
            if r is None:
                unknown += 1
            elif r < min(need, 3):
                fails.append(CHEM_LABEL[cls]); deficit += need - r
        if pack.get("tmax_req") is not None and th["tmax_c"] < pack["tmax_req"] + 10:
            fails.append(L("temperatura", "temperature")); deficit += 2
        if pack.get("outdoor") and th["uv"] < 2:
            fails.append(L("UV", "UV")); deficit += 1
        if pack.get("flame_need", 0) >= 2 and th["flame"] < 2:
            fails.append(L("trudnopalność", "flame resistance")); deficit += 2
        if _prop_need(pack, "abrasion") >= 2 and th["abrasion"] < 2:
            fails.append(L("ścieranie", "abrasion")); deficit += 1
        fam = material["family"]
        if "glass" in fam and th["fibre"] not in ("PTFE", "meta-aramid", "para-aramid"):
            fails.append(L("zgodność z włóknem szklanym (wymagana nić PTFE/aramid)", "compatibility with glass fibre (PTFE/aramid thread required)")); deficit += 3
        if "ptfe" in fam and "glass" in fam and th["fibre"] != "PTFE":
            deficit += 0.5
        best.append((len(fails), deficit, unknown, th["cost_index"], th["id"], th, fails))
    best.sort(key=lambda x: x[:5])
    nf, _, unk, _, _, th, fails = best[0]
    t = eff["thickness_max_mm"]
    target = 40 if t <= 0.40 else 70 if t <= 0.9 else 90 if t <= 1.4 else 135 if t <= 2.2 else 210
    sizes = sorted(th["sizes_tex"])
    tex = next((s for s in sizes if s >= target), sizes[-1])
    nm = NEEDLE_BY_TEX[tex]
    warn = []
    if tex < target:
        warn.append(L(f"Wybrana nić ma ograniczony zakres grubości (maks. Tex {tex}) — dla tego materiału zalecane Tex {target}; wymagana próba wytrzymałości szwu.",
                      f"Selected thread has a limited size range (max Tex {tex}) - Tex {target} recommended for this material; seam-strength trial required."))
    if nf:
        warn.append(L("Żadna nić z bazy nie spełnia wszystkich wymagań: " + ", ".join(f["pl"] for f in fails), "No catalogue thread meets all requirements: " + ", ".join(f["en"] for f in fails)))
    return dict(thread=th, tex=tex, nm_approx=round(1000 / tex), needle_nm=nm, fails=fails, meets_all=nf == 0, warnings=warn, unknown=unk)


def stitch_spec(material, pack, eff, seam):
    t = eff["thickness_max_mm"]
    sl = 3.0 if t < 0.6 else 3.5 if t < 1.0 else 4.0 if t < 1.6 else 5.0
    if seam.get("seal"):
        sl = min(sl, 3.5)
    coated = material["family"] not in UNCOATED
    point = L("R (okrągła) — minimalne uszkodzenie powłoki", "R (round point) - minimal coating damage") if coated else L("R/S (okrągła lub lekko kulista)", "R/S (round or light ball point)")
    if "glass" in material["family"] or "ptfe" in material["family"] or "aramid" in material["family"]:
        point = L("R (okrągła), igły powlekane tytanem (zużycie na włóknach szklanych/aramidowych)", "R (round), titanium-coated needles (wear on glass/aramid fibres)")
    return dict(stitch_type=L("301 (stębnówka), 2 rzędy, rozstaw 6 mm", "301 lockstitch, 2 rows, 6 mm row spacing"), stitch_length_mm=sl,
                stitches_per_cm=round(10.0 / sl, 1), seam_type=L("szew zakładkowy, 2 rzędy (ISO 4916, klasa 2)", "lapped seam, 2 rows (ISO 4916 class 2)"),
                needle_point=point, needle_system=L("system 134 / 135×17 dla maszyn z transportem złożonym — zweryfikować z instrukcją maszyny", "system 134 / 135x17 for compound-feed machines - verify with the machine manual"),
                allowance=seam["allowance"], hem=seam["hem"], seal=seam.get("seal"))


def max_layers(seams, seam):
    hem_l = 3 if seam["hem_double_fold"] else 2
    has_seam = any(s["kind"] in ("seam", "zipper", "velcro", "patch") for s in seams)
    base = max([s["layers"] for s in seams] or [2])
    cross = 2 * hem_l if has_seam else hem_l
    extra = 1 if any(s["kind"] in ("zipper", "velcro", "patch") for s in seams) else 0
    return max(base, cross + extra)


def select_machine(machines, material, pack, eff, seams, plan, stitch, thr, reqs):
    layers = max_layers(seams, plan["seam"])
    t_req = layers * eff["thickness_max_mm"]
    circ = [s for s in plan["sections"] if s.get("closure") == "sewn"]
    min_d = None
    if circ:
        dd = []
        for s in circ:
            seg = plan["segs"][s["seg"]]
            dd.append(G.circumference(seg, eff["thickness_mm"]) / math.pi)
        min_d = min(dd)
    cands = [m for m in machines if m["type"] != "welding"]
    ok = []
    for m in cands:
        if m["max_thickness_mm"] < t_req * 1.2:
            continue
        if m["max_tex"] < thr["tex"] or m["max_needle_nm"] < thr["needle_nm"][1]:
            continue
        if min_d is not None:
            if m["bed"] not in ("post", "cylinder"):
                continue
            if m["min_tube_diameter_mm"] and m["min_tube_diameter_mm"] > min_d:
                continue
        elif m["bed"] != "flat":
            continue
        ok.append(m)
    ok.sort(key=lambda m: (m["max_thickness_mm"], m["max_tex"]))
    pick = ok[0] if ok else None
    weld = next((m for m in machines if m["type"] == "welding"), None) if material.get("thermoplastic_coating") else None
    fn = "slow" if (material.get("thermoplastic_coating") or "ptfe" in material["family"]) else "std"
    speed = 2000 if t_req <= 2 else 1500 if t_req <= 4 else 1000 if t_req <= 6 else 700
    if fn == "slow":
        speed = int(speed * 0.8)
    if pick:
        speed = min(speed, pick["max_speed_spm"])
    foot = L("stopka dolna + górna z transportem złożonym (walking foot); dla powłok przylepnych stopka teflonowa/rolkowa", "compound-feed walking foot; Teflon/roller foot for sticky coatings")
    settings = dict(speed_spm=speed, foot=foot, thread_tension=L("start: naciąg zbalansowany — dokręcać nić górną aż do ułożenia splotu w środku szwu (wartość zależna od modelu maszyny)", "start: balanced tension - increase top tension until the lock sits mid-seam (machine specific)"),
                    foot_pressure=L("start: średnio-wysoki (ok. 60–70% zakresu regulacji sprężyny); skorygować, aby warstwy nie przesuwały się względem siebie", "start: medium-high (approx. 60-70% of spring range); adjust until layers do not creep"),
                    feed=pick["feed"] if pick else None)
    return dict(machine=pick, layers=layers, required_thickness_mm=t_req, circular_min_diameter_mm=min_d, settings=settings,
                alternative=weld, thread_to_check=thr["tex"], trial_required=True,
                error=None if pick else L(f"Brak klasy maszyny w bazie spełniającej: grubość ≥ {t_req * 1.2:.1f} mm, Tex {thr['tex']}, igła Nm {thr['needle_nm'][1]}" + (f", szew kołowy Ø{min_d:.0f} mm" if min_d else "") + ".",
                                          f"No machine class in the catalogue meets: thickness >= {t_req * 1.2:.1f} mm, Tex {thr['tex']}, needle Nm {thr['needle_nm'][1]}" + (f", circular seam dia {min_d:.0f} mm" if min_d else "") + "."))


def select_accessory(accs, category, pack, material=None):
    cn = _chem_needs(pack)
    scored = []
    for a in accs:
        if a["category"] != category:
            continue
        fails, unk = [], 0
        for cls, need in cn.items():
            if cls not in a["chem"]:
                continue
            r = a["chem"][cls]
            if r is None:
                unk += 1
            elif r < min(need, 3):
                fails.append(CHEM_LABEL[cls])
        if pack.get("tmax_req") is not None and a["tmax_c"] < pack["tmax_req"] + 5:
            fails.append(L("temperatura", "temperature"))
        if pack.get("tmin_req") is not None and a["tmin_c"] > pack["tmin_req"]:
            fails.append(L("temperatura minimalna", "minimum temperature"))
        if pack.get("outdoor") and a["uv"] is not None and a["uv"] < 2:
            fails.append(L("UV", "UV"))
        if pack.get("flame_need", 0) >= 2 and (a.get("flame") is not None and a["flame"] < 2):
            fails.append(L("trudnopalność", "flame resistance"))
        if pack.get("waterproof_level", 0) >= 3 and category == "zipper" and not a["waterproof"]:
            unk += 1
        scored.append((len(fails), unk, a["cost_index"], a["id"], a, fails))
    scored.sort(key=lambda x: x[:4])
    if not scored:
        return None
    nf, unk, _, _, a, fails = scored[0]
    return dict(item=a, meets_all=nf == 0, fails=fails, unknown=unk)


def thread_consumption(seams, stitch, eff):
    sl = stitch["stitch_length_mm"]
    total = 0.0
    for s in seams:
        if s["length"] <= 0:
            continue
        T = s["layers"] * eff["thickness_mm"]
        per_m = (1000.0 / sl) * (2 * sl + 2 * T) / 1000.0
        total += s["length"] / 1000.0 * per_m * s["rows"]
    return total * 1.15


def bom(project_id, material_rec, eff, calc, liner_calc, thr, stitch, plan, built, accs_sel, machine, seam, reqs, pack):
    items = []

    def add(cat, name, qty, unit, spec, why, src=None, conf=None):
        items.append(dict(category=cat, name=name, qty=qty, unit=unit, spec=spec, why=why, source=src, confidence=conf))

    add("fabric", material_rec["name"], calc["buy_m"] if calc and calc.get("ok") else None, "mb",
        L(f"szerokość beli {reqs.get('roll_width_mm')} mm; gramatura i grubość: " + (f"{eff['gsm']:.0f} g/m², {eff['thickness_mm']:.2f} mm (potwierdzone)" if eff["gsm_confirmed"] and eff["thickness_confirmed"] else "wg przedziału typowego rodziny — POTWIERDZIĆ u dostawcy"),
          f"roll width {reqs.get('roll_width_mm')} mm; weight and thickness: " + (f"{eff['gsm']:.0f} g/m2, {eff['thickness_mm']:.2f} mm (confirmed)" if eff["gsm_confirmed"] and eff["thickness_confirmed"] else "typical family range - CONFIRM with supplier")),
        L("materiał główny (zalecany zakup z rezerwą i próbą)", "main material (recommended purchase incl. reserve and trial)"), material_rec["source"], material_rec["confidence"])
    if liner_calc and liner_calc.get("ok"):
        add("fabric", L("Filc aramidowy (warstwa wewnętrzna)", "Aramid felt (inner liner)"), liner_calc["buy_m"], "mb", L(f"szerokość beli {reqs.get('roll_width_mm')} mm", f"roll width {reqs.get('roll_width_mm')} mm"),
            L("druga warstwa termoizolacyjna (konstrukcja wielowarstwowa)", "second thermal layer (multilayer construction)"))
    cons = thread_consumption(built["seams"], stitch, eff)
    th = thr["thread"]
    add("thread", th["name"], round(cons * 1.1 + 20, 0), "m", L(f"Tex {thr['tex']} (≈ Nm {thr['nm_approx']}); zużycie obliczone z długości szwów × rzędy × długość ściegu", f"Tex {thr['tex']} (approx. Nm {thr['nm_approx']}); consumption computed from seam length x rows x stitch length"),
        L("nić do szycia głównego i wykończeń", "thread for main seams and finishing"), th["source"], th["confidence"])
    add("needle", L(f"Igły Nm {thr['needle_nm'][0]}–{thr['needle_nm'][1]}", f"Needles Nm {thr['needle_nm'][0]}-{thr['needle_nm'][1]}"), 10, "szt.", stitch["needle_point"], L("zapas igieł na próbę i produkcję", "spare needles for trial and production"))

    def sel_name(k):
        return accs_sel[k]["item"]["name"] if accs_sel.get(k) else L("(brak pozycji w bazie)", "(no catalogue item)")
    zl = sum(z["length"] for z in built["zippers"])
    if zl:
        a = accs_sel["zipper"]["item"]
        add("accessory", a["name"], round(zl / 1000 * 1.05, 2), "m", L(f"odcinki: " + ", ".join(f"{z['section']}={z['length']:.0f} mm" for z in built["zippers"]) + f"; rozmiar {a['size']}", "sections: " + ", ".join(f"{z['section']}={z['length']:.0f} mm" for z in built["zippers"]) + f"; size {a['size']}"),
            L("zamknięcie wzdłużne modułów", "longitudinal closure of modules"), a["source"], a["confidence"])
        add("accessory", L("Suwaki do zamków", "Zipper sliders"), len(built["zippers"]) * 1, "szt.", L("po 1 na odcinek", "1 per run"), L("suwaki dobrać do rozmiaru zamka", "match sliders to zipper size"))
    vl = sum(v["length"] for v in built["velcro"])
    if vl:
        a = accs_sel["hook_loop"]["item"]
        add("accessory", a["name"], round(vl / 1000 * 1.1, 2), "m", L("paski 25 mm: haczyki + pętelki", "25 mm strips: hook + loop"), L("zamknięcie sekcji harmonijkowych / modułów", "closure of bellows sections / modules"), a["source"], a["confidence"])
    sn = sum(s["count"] for s in built["snaps"])
    if sn:
        a = accs_sel["snap"]["item"]
        add("accessory", a["name"], sn, "kpl.", a["size"], L("zamknięcie na zatrzaski", "snap closure"), a["source"], a["confidence"])
    # cinches at free ends
    cinch_len = 0.0
    n_cinch = 0
    for sc in plan["sections"]:
        seg = plan["segs"][sc["seg"]]
        cmean = G.circumference(seg, eff["thickness_mm"])
        if sc["start_finish"] in ("hem", "skirt"):
            cinch_len += cmean + 150; n_cinch += 1
        if sc["end_finish"] == "hem":
            cinch_len += cmean + 150; n_cinch += 1
    if reqs.get("elastic") and accs_sel.get("elastic"):
        a = accs_sel["elastic"]["item"]
        add("accessory", a["name"], round(cinch_len / 1000, 2), "m", L(f"{n_cinch} ściągaczy (obwód + 150 mm na zawiązanie)", f"{n_cinch} cinches (circumference + 150 mm for tying)"), L("ściągacze na końcach modułów (kanał w rąbku)", "cinches at module ends (hem channel)"), a["source"], a["confidence"])
    elif n_cinch and accs_sel.get("webbing") and accs_sel.get("buckle"):
        w, b = accs_sel["webbing"]["item"], accs_sel["buckle"]["item"]
        add("accessory", w["name"], round(cinch_len / 1000, 2), "m", L(f"{n_cinch} pasków zaciskowych", f"{n_cinch} cinch straps"), L("paski zaciskowe na końcach modułów", "cinch straps at module ends"), w["source"], w["confidence"])
        add("accessory", b["name"], n_cinch, "szt.", b["size"], L("klamry pasków zaciskowych", "cinch strap buckles"), b["source"], b["confidence"])
    bl = sum(b["length"] for b in built["bindings"])
    if bl and accs_sel.get("binding"):
        a = accs_sel["binding"]["item"]
        add("accessory", a["name"], round(bl / 1000 * 1.1, 2), "m", a["size"], L("obszycie otworów technologicznych", "binding of technological openings"), a["source"], a["confidence"])
    if seam.get("seal") and accs_sel.get("seam_tape"):
        a = accs_sel["seam_tape"]["item"]
        sl = sum(s["length"] for s in built["seams"] if s["kind"] in ("seam", "patch"))
        add("accessory", a["name"], round(sl / 1000 * 1.1, 2), "m" if a["size"] != "pasta" else "m (szew)", seam["seal"]["text"], L("uszczelnienie szwów (wymóg szczelności)", "seam sealing (tightness requirement)"), a["source"], a["confidence"])
    if pack.get("waterproof_level", 0) >= 3 and zl and accs_sel.get("gasket"):
        a = accs_sel["gasket"]["item"]
        add("accessory", a["name"], round(zl / 1000 * 1.05, 2), "m", a["size"], L("uszczelka zakładki zamka", "zipper flap gasket"), a["source"], a["confidence"])
    patches = len([p for p in built["pieces"] if p["kind"] == "patch"])
    if patches:
        add("note", L("Wzmocnienia otworów", "Opening patches"), patches, "szt.", L("wycinane z materiału głównego (ujęte w zakupie)", "cut from the main material (included in purchase)"), L("wzmocnienia", "reinforcement"))
    return items
