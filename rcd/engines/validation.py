"""Validation module. GREEN only when the requirement is met AND based on confirmed data or deterministic computation.
YELLOW = probably met / needs verification. RED = not met or significant risk (blocks approval)."""
import math
from ..i18n import L
from . import geometry as G

G_, Y_, R_ = "green", "yellow", "red"


def chk(id, label, status, detail, basis):
    return dict(id=id, label=label, status=status, detail=detail, basis=basis)


def validate(ctx):
    segs, pack, rec, plan, built, calc, thr, mach, sew, acc, reqs, eff = (ctx[k] for k in
        ("segs", "pack", "rec", "plan", "built", "calc", "thr", "mach", "stitch", "accs", "reqs", "eff"))
    out = []
    det = L("obliczenie deterministyczne", "deterministic computation")
    cat = L("dane typowe z katalogu (niezweryfikowane)", "typical catalogue data (unverified)")
    # 1 material vs environment
    fails = rec["fails"]
    if fails:
        out.append(chk("material_env", L("Materiał spełnia wymagania środowiskowe", "Material meets environmental requirements"), R_,
                       L("Niespełnione: " + "; ".join(f["label"]["pl"] for f in fails), "Not met: " + "; ".join(f["label"]["en"] for f in fails)), cat))
    else:
        unv = not rec.get("verified_all")
        unk = [c for c in rec["checks"] if c["status"] in ("unknown", "marginal", "test")]
        st = G_ if not unv and not unk else Y_
        out.append(chk("material_env", L("Materiał spełnia wymagania środowiskowe", "Material meets environmental requirements"), st,
                       L("Wymagania spełnione wg danych katalogowych" + (", ale dane nie są potwierdzone kartą TDS." if unv else ".") + (f" Pozycje do weryfikacji: {len(unk)}." if unk else ""),
                         "Requirements met per catalogue data" + (", but data are not confirmed by a TDS." if unv else ".") + (f" Items to verify: {len(unk)}." if unk else "")), cat))
    cu = pack["critical_unresolved"]
    out.append(chk("env_unresolved", L("Kompletność analizy środowiska", "Completeness of environment analysis"), Y_ if cu else G_,
                   L(f"{len(cu)} istotnych czynników bez odpowiedzi (nieznane ≠ nieobecne) — uzupełnij lub potwierdź brak.", f"{len(cu)} critical factors unanswered (unknown != absent) - complete or confirm absence.") if cu
                   else L("Wszystkie istotne czynniki rozstrzygnięte.", "All critical factors resolved."), det))
    # 2 thickness/mass
    mass = None
    if calc.get("ok"):
        mass = sum(p["area_m2"] for p in built["pieces"]) * eff["gsm"] / 1000.0 * (1 + 0.1)
    lim = reqs.get("max_mass_kg")
    if lim not in (None, "") and mass is not None:
        out.append(chk("mass", L("Masa pokrowca", "Cover mass"), R_ if mass > float(lim) else (Y_ if not eff["gsm_confirmed"] else G_),
                       L(f"Szacunek {mass:.2f} kg (materiał + ok. 10% dodatków), limit {float(lim):g} kg" + ("; gramatura niepotwierdzona." if not eff["gsm_confirmed"] else "."),
                         f"Estimate {mass:.2f} kg (material + approx. 10% accessories), limit {float(lim):g} kg" + ("; weight unconfirmed." if not eff["gsm_confirmed"] else ".")), det))
    else:
        out.append(chk("mass", L("Masa pokrowca", "Cover mass"), G_ if mass is not None else Y_,
                       L(f"Szacunek {mass:.2f} kg; brak limitu masy." if mass is not None else "Nie obliczono.", f"Estimate {mass:.2f} kg; no mass limit set." if mass is not None else "Not computed."), det))
    # 3 flex
    flex_need = max([r["need"] for r in pack["requirements"] if r["key"] == "flex"] or [0])
    fr = rec["mechanical"]
    flex_r = next((m["rating"] for m in fr if m["key"] == "flex"), None)
    bell = [s for s in plan["sections"] if s["kind"] == "bellows"]
    if flex_r is not None and flex_r < flex_need:
        st, d = R_, L("Odporność na zginanie materiału poniżej wymaganej.", "Material flex resistance below required.")
    elif bell and rec.get("crease_sensitive"):
        st, d = R_, L("Materiał wrażliwy na zagięcia w sekcjach harmonijkowych.", "Crease-sensitive material in bellows sections.")
    else:
        st, d = Y_, L("Zginanie wg danych typowych; wymagana próba zmęczeniowa na stanowisku/stole prób.", "Flexing per typical data; fatigue trial on the cell/test rig required.")
    out.append(chk("flex", L("Materiał pozwala na wymagane zginanie", "Material allows the required flexing"), st, d, cat))
    # 4 motion clearance
    cl = ctx["clearance"]
    gap = cl.get("gap")
    coplanar = bool(reqs.get("bend_axes_coplanar", True))
    if gap is None:
        out.append(chk("clearance", L("Brak kolizji pokrowca przy ruchu robota", "No cover collision during robot motion"), Y_, L("Brak niesąsiednich segmentów do sprawdzenia.", "No non-adjacent segments to check."), det))
    elif gap < 0:
        out.append(chk("clearance", L("Brak kolizji pokrowca przy ruchu robota", "No cover collision during robot motion"), R_,
                       L(f"Kolizja osłon {cl['pair'][0]} ↔ {cl['pair'][1]}: przenikanie {-gap:.0f} mm przy {cl['config']}. Zmniejsz luz/średnice lub zmień zakres osi.",
                         f"Cover collision {cl['pair'][0]} <-> {cl['pair'][1]}: {-gap:.0f} mm penetration at {cl['config']}. Reduce clearance/diameters or axis range."), det))
    else:
        out.append(chk("clearance", L("Brak kolizji pokrowca przy ruchu robota", "No cover collision during robot motion"), Y_ if gap < 15 or True else G_,
                       L(f"Min. odstęp osłon {gap:.0f} mm ({cl['samples']} pozycji, model PŁASKI, osie zginane współpłaszczyznowe). Potwierdzić na modelu 3D / w ruchu rzeczywistym.",
                         f"Min. cover gap {gap:.0f} mm ({cl['samples']} poses, PLANAR model, coplanar bending axes). Confirm on the 3D model / real motion."), det))
    # 5 pattern dims
    bad = []
    t = eff["thickness_mm"]
    for p in built["pieces"]:
        f, a = p["finished"], p["allowances"]
        if f["shape"] == "rect":
            x0 = min(q[0] for q in p["cut"]); y0 = min(q[1] for q in p["cut"]); x1 = max(q[0] for q in p["cut"]); y1 = max(q[1] for q in p["cut"])
            ew = (f["width"] + a["left"] + a["right"]) * (1 + eff["shrink_weft_pct"] / 100)
            eh = (f["length"] + a["start"] + a["end"]) * (1 + eff["shrink_warp_pct"] / 100)
            if abs((x1 - x0) - ew) > 0.01 or abs((y1 - y0) - eh) > 0.01:
                bad.append(p["id"])
    out.append(chk("pattern_dims", L("Wymiary wykrojów poprawne (gotowy ↔ wykrój)", "Pattern dimensions correct (finished <-> cut)"), R_ if bad else G_,
                   L("Niezgodność: " + ", ".join(bad), "Mismatch: " + ", ".join(bad)) if bad else
                   L("Wymiar wykroju = wymiar gotowy + zapasy (×skurcz) dla wszystkich elementów prostokątnych; obwody obliczone z (Ø + 2·luz + grubość).",
                     "Cut size = finished size + allowances (x shrinkage) for all rectangular pieces; circumferences from (dia + 2 x clearance + thickness)."), det))
    sh = eff["shrink_confirmed"]
    out.append(chk("allowances", L("Uwzględniono wszystkie zapasy (szwy, rąbki, zakładki, grubość, skurcz)", "All allowances included (seams, hems, overlaps, thickness, shrinkage)"), G_ if sh else Y_,
                   L("Zapasy przypisane do każdej krawędzi." + ("" if sh else " Skurcz/rozciągliwość materiału niepotwierdzone (przyjęto 0%) — zmierz na próbce."), "Allowances assigned to every edge." + ("" if sh else " Material shrinkage/stretch unconfirmed (0% assumed) - measure on a sample.")), det))
    # 6 quantity
    if calc.get("ok"):
        area_pieces = sum(p["area_m2"] for p in built["pieces"])
        enough = calc["buy_m"] * calc["roll_width_mm"] / 1000 >= area_pieces * 1.0
        out.append(chk("quantity", L("Ilość materiału wystarczająca", "Material quantity sufficient"), G_ if enough else R_,
                       L(f"Zakup {calc['buy_m']:.1f} mb vs rozmieszczenie {calc['marker_length_m']:.2f} mb (straty {calc['waste_pct']:.0f}%, rezerwa {calc['reserve_pct']:.0f}%).", f"Purchase {calc['buy_m']:.1f} m vs marker {calc['marker_length_m']:.2f} m (waste {calc['waste_pct']:.0f}%, reserve {calc['reserve_pct']:.0f}%)."), det))
    else:
        out.append(chk("quantity", L("Ilość materiału wystarczająca", "Material quantity sufficient"), R_, calc.get("error", L("Brak obliczeń", "Not computed")), det))
    # 7 thread
    th = thr
    out.append(chk("thread", L("Nić zgodna z materiałem i środowiskiem", "Thread compatible with material and environment"), R_ if not th["meets_all"] else Y_,
                   (L("Brak nici spełniającej wszystkie wymagania: ", "No thread meets all requirements: ") if False else (th["warnings"][0] if th["warnings"] else L(f"{th['thread']['name']['pl']}, Tex {th['tex']} — dane typowe; próba wytrzymałości szwu wymagana.", f"{th['thread']['name']['en']}, Tex {th['tex']} - typical data; seam-strength trial required."))), cat))
    # 8 machine
    if mach["machine"]:
        out.append(chk("machine", L("Maszyna poradzi sobie z grubością i liczbą warstw", "Machine can handle thickness and layer count"), Y_,
                       L(f"Klasa: {mach['machine']['name']['pl']}; wymagane {mach['layers']} warstw × {eff['thickness_max_mm']:.2f} mm = {mach['required_thickness_mm']:.1f} mm (zapas ≥20%). Parametry klasy typowe — sprawdź w katalogu modelu, wykonaj próbę.",
                         f"Class: {mach['machine']['name']['en']}; {mach['layers']} layers x {eff['thickness_max_mm']:.2f} mm = {mach['required_thickness_mm']:.1f} mm required (>=20% margin). Class parameters typical - check the model catalogue, run a trial."), cat))
    else:
        out.append(chk("machine", L("Maszyna poradzi sobie z grubością i liczbą warstw", "Machine can handle thickness and layer count"), R_, mach["error"], cat))
    # 9 accessories
    af = [(k, v) for k, v in acc.items() if v and not v["meets_all"]]
    out.append(chk("accessories", L("Zamki i dodatki odpowiednie do środowiska", "Zippers and accessories suitable for the environment"), R_ if af else Y_,
                   L("Nie spełniają: " + "; ".join(f"{k}: " + ", ".join(x['pl'] for x in v['fails']) for k, v in af), "Not met: " + "; ".join(f"{k}: " + ", ".join(x['en'] for x in v['fails']) for k, v in af)) if af else
                   L("Dobrane wg danych typowych klas wyrobów — potwierdzić kartami produktów.", "Selected from typical product-class data - confirm with product datasheets."), cat))
    # 10 removability
    probs = [e for e in plan["errors"]]
    out.append(chk("removable", L("Pokrowiec można zamontować i zdemontować", "Cover can be fitted and removed"), R_ if probs else G_,
                   probs[0]["text"] if probs else L(f"{len(plan['modules'])} modułów, zapięcia przypisane do każdej sekcji.", f"{len(plan['modules'])} modules, closures assigned to every section."), det))
    # 11 hot surface
    hot = [s for s in segs if s["cover"] and s.get("hot_c") is not None and s["hot_c"] > rec["tmax_c"] - 10]
    out.append(chk("hot_surface", L("Brak kontaktu z gorącymi elementami powyżej limitu materiału", "No contact with hot parts above the material limit"), R_ if hot else G_,
                   L("Powierzchnia > limit materiału −10 K: " + ", ".join(s["name"] for s in hot), "Surface above material limit -10 K: " + ", ".join(s["name"] for s in hot)) if hot else
                   L("Temperatury powierzchni segmentów w limicie materiału (z marginesem 10 K).", "Segment surface temperatures within material limit (10 K margin)."), det))
    # 12 safety / access
    notes = []
    st = Y_
    cool = [s["name"] for s in segs if s["cover"] and s["cooling_vent"]]
    if cool:
        notes.append(L("chłodzenie: " + ", ".join(cool), "cooling: " + ", ".join(cool)))
    svc = [s["name"] for s in segs if s["cover"] and s["service"]]
    if svc and not any(o.get("type") == "keepout" for s in segs for o in s["openings"]):
        notes.append(L("dostęp serwisowy: " + ", ".join(svc) + " (brak otworów serwisowych — zapewnić zdejmowanie modułu)", "service access: " + ", ".join(svc) + " (no service openings - ensure module removal)"))
    esd = any(r["key"] == "esd" for r in pack["requirements"])
    if esd:
        notes.append(L("ESD: uziemienie i rezystancja wymagają pomiaru na gotowym wyrobie", "ESD: grounding and resistance must be measured on the finished product"))
    out.append(chk("safety", L("Ograniczenia bezpieczeństwa (sensory, chłodzenie, serwis, ESD, pożar)", "Safety constraints (sensors, cooling, service, ESD, fire)"), Y_,
                   L("Pokrowiec jest dodatkowym wyposażeniem maszyny: wymagana ocena ryzyka i walidacja na stanowisku. System nie deklaruje zgodności z normami. " , "The cover is additional machine equipment: risk assessment and on-site validation required. The system makes no standards-compliance claims. ")
                   if not notes else L("Wymagana ocena ryzyka i walidacja na stanowisku; brak deklaracji zgodności z normami. Uwagi: ", "Risk assessment and on-site validation required; no standards-compliance claims. Notes: ") , L("wymaga weryfikacji w rzeczywistym środowisku", "requires on-site verification")))
    if notes:
        out[-1]["notes"] = notes
    # 13 geometry warnings
    w = plan["warnings"] + built["warnings"]
    out.append(chk("geometry_warn", L("Ostrzeżenia konstrukcyjne i wykrojowe", "Construction and pattern warnings"), Y_ if w else G_,
                   L(f"{len(w)} ostrzeżeń (patrz Cover Design / Pattern).", f"{len(w)} warnings (see Cover Design / Pattern).") if w else L("Brak ostrzeżeń.", "No warnings."), det))
    # 14 data provenance
    prov = [k for k, v in (("material", "verified" if rec.get("verified_all") else "x"), ("thread", th["thread"]["confidence"]), ("machine", (mach["machine"] or {}).get("confidence"))) if v != "verified"]
    out.append(chk("provenance", L("Źródła danych potwierdzone dokumentacją", "Data sources confirmed by documentation"), Y_ if prov else G_,
                   L("Niepotwierdzone dokumentem: " + ", ".join(prov) + ". Dodaj kartę TDS/źródło w module bazy danych, aby podnieść status.", "Not confirmed by a document: " + ", ".join(prov) + ". Add a TDS/source in the database module to raise the status.") if prov else L("Wszystko potwierdzone.", "All confirmed."), det))
    return out


def summary(checks):
    r = sum(1 for c in checks if c["status"] == R_); y = sum(1 for c in checks if c["status"] == Y_); g = sum(1 for c in checks if c["status"] == G_)
    return dict(red=r, yellow=y, green=g, can_approve=r == 0)
