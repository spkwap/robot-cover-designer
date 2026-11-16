"""Environment analysis module: factor registry, completeness check, requirement derivation,
and a rule-based text assistant (suggestions only - never auto-applied, never produces numbers)."""
import re
from ..i18n import L

FACTORS = []


def _f(key, group, kind, pl, en, critical=False):
    FACTORS.append(dict(key=key, group=group, kind=kind, label=L(pl, en), critical=critical))


for k, pl, en in [("oil_industrial", "Oleje przemysłowe", "Industrial oils"), ("oil_hydraulic", "Oleje hydrauliczne", "Hydraulic oils"),
                  ("oil_cutting", "Oleje chłodząco-smarujące", "Cutting/cooling lubricant oils"), ("grease", "Smary", "Greases"),
                  ("emulsion", "Emulsje chłodzące", "Cooling emulsions"), ("solvents", "Rozpuszczalniki", "Solvents"),
                  ("detergents", "Detergenty przemysłowe", "Industrial detergents"), ("disinfectants", "Środki dezynfekujące", "Disinfectants"),
                  ("acids", "Kwasy", "Acids"), ("alkalis", "Zasady", "Alkalis"),
                  ("aggressive_chem", "Substancje agresywne chemicznie", "Chemically aggressive substances"),
                  ("process_fluids", "Płyny technologiczne (inne)", "Other process fluids"),
                  ("fuels", "Paliwa i substancje ropopochodne", "Fuels and petroleum products")]:
    _f(k, "chem", "freq", pl, en, critical=k != "process_fluids" and k != "grease")
for k, pl, en, crit in [("dust_industrial", "Pył przemysłowy", "Industrial dust", True), ("dust_metal", "Pył metaliczny", "Metal dust", True),
                        ("dust_wood", "Pył drzewny", "Wood dust", False), ("dust_plastic", "Pył tworzyw sztucznych", "Plastic dust", False),
                        ("metal_chips", "Opiłki/wióry metalu", "Metal chips", True), ("spatter", "Odpryski (np. spawalnicze)", "Spatter (e.g. welding)", True),
                        ("sparks", "Iskry", "Sparks", True), ("hot_particles", "Gorące cząstki", "Hot particles", False),
                        ("abrasion", "Ścieranie mechaniczne", "Mechanical abrasion", True), ("friction", "Tarcie", "Friction", False),
                        ("impact", "Uderzenia", "Impacts", True), ("tear", "Rozdarcia", "Tearing", False), ("puncture", "Przebicia", "Puncture", False),
                        ("vibration", "Wibracje", "Vibration", False), ("moisture", "Wilgoć", "Moisture", False),
                        ("splash", "Zachlapania", "Splashes", True), ("water_jets", "Strumienie wody", "Water jets", True),
                        ("pressure_wash", "Mycie ciśnieniowe", "Pressure washing", True)]:
    _f(k, "phys", "freq" if k in ("splash", "water_jets", "pressure_wash") else "sev", pl, en, crit)
for k, pl, en, kind in [("hot_contact", "Kontakt z gorącymi elementami", "Contact with hot parts", "bool"),
                        ("radiant_heat", "Promieniowanie cieplne", "Radiant heat", "sev"),
                        ("thermal_shock", "Nagłe zmiany temperatury", "Sudden temperature changes", "bool"),
                        ("cold_room", "Praca w chłodni", "Cold-room operation", "bool"),
                        ("near_furnace", "Praca w pobliżu pieców", "Operation near furnaces", "bool")]:
    _f(k, "thermal", kind, pl, en, k in ("hot_contact", "radiant_heat"))
for k, pl, en, kind, crit in [("condensation", "Kondensacja pary wodnej", "Condensation", "sev", False), ("water_contact", "Kontakt z wodą", "Water contact", "freq", False),
                              ("steam", "Para wodna", "Steam", "sev", True), ("uv", "Promieniowanie UV", "UV radiation", "sev", True),
                              ("outdoor", "Warunki zewnętrzne", "Outdoor conditions", "bool", True),
                              ("pressure_change", "Zmiany ciśnienia", "Pressure changes", "bool", False)]:
    _f(k, "atmos", kind, pl, en, crit)
for k, pl, en, kind in [("speed", "Duża prędkość pracy", "High working speed", "sev"), ("accel", "Duże przyspieszenia", "High accelerations", "sev"),
                        ("intensity", "Intensywność eksploatacji", "Duty intensity", "sev"),
                        ("continuous_bending", "Ciągłe zginanie materiału", "Continuous material bending", "sev"),
                        ("stretching", "Rozciąganie materiału", "Material stretching", "sev"), ("twisting", "Skręcanie materiału", "Material twisting", "sev"),
                        ("contact_other", "Kontakt pokrowca z innymi elementami stanowiska", "Cover contact with other cell elements", "sev")]:
    _f(k, "motion", kind, pl, en, k in ("continuous_bending", "contact_other"))
for k, pl, en, kind, crit in [("antistatic", "Antystatyczność", "Antistatic", "bool", True), ("conductive", "Przewodnictwo elektryczne", "Electrical conductivity", "bool", False),
                              ("esd", "Właściwości ESD", "ESD properties", "bool", True), ("flame_retardant", "Trudnopalność", "Flame retardancy", "bool", True),
                              ("weld_spark_resistance", "Odporność na iskry spawalnicze", "Welding spark resistance", "bool", False),
                              ("cut_resistance", "Odporność na przecięcia", "Cut resistance", "sev", False),
                              ("abrasion_resistance", "Wymagana odporność na ścieranie", "Required abrasion resistance", "sev", False),
                              ("soil_resistance", "Odporność na zabrudzenia", "Soil resistance", "sev", False),
                              ("easy_cleaning", "Łatwość czyszczenia", "Easy cleaning", "bool", False),
                              ("waterproof", "Wodoodporność", "Waterproofness", "bool", True), ("dust_tight", "Pyłoszczelność", "Dust-tightness", "bool", True),
                              ("antimicrobial", "Odporność na mikroorganizmy", "Antimicrobial resistance", "bool", False)]:
    _f(k, "special", kind, pl, en, crit)

FACTOR_BY_KEY = {f["key"]: f for f in FACTORS}
LEVEL_LABELS = {"freq": [L("sporadyczny", "sporadic"), L("regularny", "regular"), L("ciągły", "continuous")],
                "sev": [L("niskie", "low"), L("średnie", "medium"), L("wysokie", "high")],
                "bool": [L("występuje", "present")] * 3}

CHEM_MAP = {"oil_industrial": ["mineral_oil"], "oil_hydraulic": ["mineral_oil"], "grease": ["mineral_oil"],
            "oil_cutting": ["cutting_fluid", "mineral_oil"], "emulsion": ["cutting_fluid"], "solvents": ["solvents"],
            "detergents": ["detergents"], "disinfectants": ["disinfectants"], "acids": ["acids"], "alkalis": ["alkalis"],
            "aggressive_chem": ["acids", "alkalis", "solvents"], "fuels": ["fuels"]}
CHEM_LABEL = {"mineral_oil": L("oleje mineralne/smary", "mineral oils/greases"), "cutting_fluid": L("płyny chłodząco-smarujące", "cutting fluids"),
              "solvents": L("rozpuszczalniki", "solvents"), "detergents": L("detergenty", "detergents"),
              "disinfectants": L("środki dezynfekujące", "disinfectants"), "acids": L("kwasy", "acids"),
              "alkalis": L("zasady", "alkalis"), "fuels": L("paliwa", "fuels")}
PROP_LABEL = {"abrasion": L("odporność na ścieranie", "abrasion resistance"), "tear": L("odporność na rozdarcie", "tear resistance"),
              "cut": L("odporność na przecięcie", "cut resistance"), "puncture": L("odporność na przebicie", "puncture resistance"),
              "flex": L("odporność na zginanie", "flex fatigue resistance"), "flame": L("trudnopalność", "flame resistance"),
              "spark": L("odporność na iskry/odpryski", "spark/spatter resistance"), "esd": L("antystatyczność/ESD", "antistatic/ESD"),
              "uv": L("odporność na UV", "UV resistance"), "water": L("wodoodporność", "water resistance"),
              "cleanability": L("łatwość czyszczenia", "cleanability"), "dust": L("szczelność na pył", "dust tightness"),
              "antimicrobial": L("odporność na mikroorganizmy", "antimicrobial resistance")}
RATING_LABEL = [L("brak", "none"), L("ograniczona", "limited"), L("dobra", "good"), L("bardzo dobra", "excellent")]

LVL = lambda m: (lambda l: m[l])


def _m(a, b, c):
    return {1: a, 2: b, 3: c}


PROP_MAP = {
    "dust_industrial": [("dust", _m(1, 2, 2))], "dust_metal": [("dust", _m(1, 2, 2)), ("abrasion", _m(1, 2, 2))],
    "dust_wood": [("dust", _m(1, 2, 2))], "dust_plastic": [("dust", _m(1, 2, 2))],
    "metal_chips": [("puncture", _m(1, 2, 3)), ("cut", _m(1, 2, 3))],
    "spatter": [("spark", _m(3, 3, 3))], "sparks": [("spark", _m(2, 2, 3))], "hot_particles": [("spark", _m(2, 2, 3))],
    "abrasion": [("abrasion", _m(1, 2, 3))], "friction": [("abrasion", _m(1, 2, 3))],
    "impact": [("tear", _m(1, 2, 3)), ("puncture", _m(1, 1, 2))], "tear": [("tear", _m(1, 2, 3))], "puncture": [("puncture", _m(1, 2, 3))],
    "vibration": [("flex", _m(1, 2, 2))],
    "moisture": [("water", _m(1, 1, 2))], "splash": [("water", _m(1, 2, 2))], "water_jets": [("water", _m(2, 2, 3))],
    "pressure_wash": [("water", _m(3, 3, 3))], "water_contact": [("water", _m(1, 2, 2))], "condensation": [("water", _m(1, 1, 2))],
    "steam": [("water", _m(2, 2, 2))], "uv": [("uv", _m(1, 2, 3))], "outdoor": [("uv", _m(2, 2, 2)), ("water", _m(1, 1, 1))],
    "radiant_heat": [("flame", _m(2, 2, 2))], "near_furnace": [("flame", _m(2, 2, 2))],
    "flame_retardant": [("flame", _m(2, 2, 2))], "weld_spark_resistance": [("spark", _m(3, 3, 3)), ("flame", _m(2, 2, 2))],
    "cut_resistance": [("cut", _m(1, 2, 3))], "abrasion_resistance": [("abrasion", _m(1, 2, 3))],
    "soil_resistance": [("cleanability", _m(1, 2, 2))], "easy_cleaning": [("cleanability", _m(2, 2, 2))],
    "waterproof": [("water", _m(2, 2, 2))], "dust_tight": [("dust", _m(3, 3, 3))], "antistatic": [("esd", _m(2, 2, 2))],
    "conductive": [("esd", _m(3, 3, 3))], "esd": [("esd", _m(3, 3, 3))], "antimicrobial": [("antimicrobial", _m(2, 2, 2))],
    "continuous_bending": [("flex", _m(2, 3, 3))], "stretching": [("flex", _m(1, 2, 3))], "twisting": [("flex", _m(1, 2, 3))],
    "contact_other": [("abrasion", _m(1, 2, 3))], "intensity": [("flex", _m(1, 2, 3))], "speed": [("flex", _m(1, 1, 2))],
    "accel": [("flex", _m(1, 1, 2))],
}


def factor_state(env, key):
    f = (env.get("factors") or {}).get(key) or {}
    st = f.get("state", "unknown")
    lvl = int(f.get("level") or 2)
    return st, max(1, min(3, lvl)), f


def completeness(env, robot=None):
    """Return blocking missing numeric inputs and questions for unresolved critical factors."""
    missing, questions = [], []
    for k, pl, en in [("tmin_c", "minimalna temperatura pracy", "minimum operating temperature"),
                      ("tmax_c", "maksymalna temperatura otoczenia", "maximum ambient temperature")]:
        if env.get(k) in (None, ""):
            missing.append(dict(key=k, text=L(f"Podaj {pl}.", f"Provide {en}.")))
    if env.get("cycles_per_day") in (None, ""):
        questions.append(dict(key="cycles_per_day", text=L("Podaj liczbę cykli ruchu na dobę (decyduje o wymaganej odporności na zginanie).",
                                                            "Provide motion cycles per day (drives the required flex resistance).")))
    for f in FACTORS:
        st, _, _ = factor_state(env, f["key"])
        if st == "unknown" and f["critical"]:
            questions.append(dict(key=f["key"], text=L(f"Czy występuje: {f['label']['pl']}? Brak odpowiedzi nie oznacza, że czynnik nie występuje.",
                                                       f"Is this present: {f['label']['en']}? No answer does not mean the factor is absent.")))
    return dict(missing=missing, questions=questions,
                unknown_total=sum(1 for f in FACTORS if factor_state(env, f["key"])[0] == "unknown"))


def derive_requirements(env, reqs, joint_info=None):
    R = {}
    unresolved = [f["key"] for f in FACTORS if factor_state(env, f["key"])[0] == "unknown"]
    critical_unresolved = [f["key"] for f in FACTORS if f["critical"] and factor_state(env, f["key"])[0] == "unknown"]

    def add(rid, typ, key, need, weight, reason):
        cur = R.get(rid)
        if cur is None or need > cur["need"]:
            R[rid] = dict(id=rid, type=typ, key=key, need=need, weight=weight, reasons=[reason])
        elif need == cur["need"]:
            cur["reasons"].append(reason)
            cur["weight"] = max(cur["weight"], weight)

    def lvl_label(f, lvl):
        return LEVEL_LABELS[f["kind"]][lvl - 1]

    for f in FACTORS:
        st, lvl, _ = factor_state(env, f["key"])
        if st != "present":
            continue
        reason = L(f"{f['label']['pl']} ({lvl_label(f, lvl)['pl']})", f"{f['label']['en']} ({lvl_label(f, lvl)['en']})")
        for cls in CHEM_MAP.get(f["key"], []):
            add(f"chem:{cls}", "chem", cls, lvl, 1 + lvl + (1 if f["critical"] else 0), reason)
        for prop, table in PROP_MAP.get(f["key"], []):
            add(f"prop:{prop}", "prop", prop, table[lvl], 1 + lvl, reason)
        if f["key"] == "process_fluids":
            add("test:process_fluids", "test", "process_fluids", 0, 3,
                L("Płyny technologiczne — odporność wyłącznie wg SDS/TDS i próby zanurzeniowej",
                  "Process fluids - resistance only per SDS/TDS and immersion test"))
    cyc = env.get("cycles_per_day")
    if cyc not in (None, ""):
        c = float(cyc)
        need = 1 if c < 1000 else (2 if c < 20000 else 3)
        add("prop:flex", "prop", "flex", need, 2 + need, L(f"{int(c)} cykli/dobę", f"{int(c)} cycles/day"))
    if joint_info and joint_info.get("needs_bellows"):
        add("prop:flex", "prop", "flex", 2, 4, L("Sekcje harmonijkowe na przegubach zginanych (zagięcia/plisy)", "Bellows sections on bending joints (folds/pleats)"))
    if reqs.get("easy_clean"):
        add("prop:cleanability", "prop", "cleanability", 2, 2, L("Wymóg łatwego czyszczenia (pokrowiec)", "Easy cleaning required (cover)"))
    if float(reqs.get("removal_per_month") or 0) >= 20:
        add("prop:abrasion", "prop", "abrasion", 2, 2, L("Częsty demontaż", "Frequent removal"))
    if env.get("industry_compliance"):
        add("cert:industry", "cert", "industry", 0, 3, L(f"Zgodność z wymaganiami branży: {env['industry_compliance']}", f"Industry compliance: {env['industry_compliance']}"))
    # temperatures
    tmax = [env.get("tmax_c"), env.get("tsurface_c"), env.get("hot_contact_c"), env.get("tpeak_c")]
    tmax_cont = [float(x) for x in tmax[:3] if x not in (None, "")]
    st_steam, _, _ = factor_state(env, "steam")
    if st_steam == "present":
        tmax_cont.append(100.0)
    tmax_req = max(tmax_cont) if tmax_cont else None
    tmin_req = float(env["tmin_c"]) if env.get("tmin_c") not in (None, "") else None
    tpeak = float(env["tpeak_c"]) if env.get("tpeak_c") not in (None, "") else None
    # hydrolysis concern
    hum = float(env["humidity_pct"]) if env.get("humidity_pct") not in (None, "") else None
    hydro = False
    for k in ("emulsion", "oil_cutting", "steam", "condensation", "water_jets", "pressure_wash"):
        if factor_state(env, k)[0] == "present":
            hydro = True
    if hum is not None and hum >= 85:
        hydro = True
    return dict(requirements=sorted(R.values(), key=lambda r: r["id"]), tmax_req=tmax_req, tmin_req=tmin_req, tpeak=tpeak,
                hydrolysis_concern=hydro and (tmax_req or 0) >= 40, unresolved=unresolved,
                critical_unresolved=critical_unresolved, no_crease_sensitive=bool(joint_info and joint_info.get("needs_bellows")),
                thermal_shock=factor_state(env, "thermal_shock")[0] == "present",
                waterproof_level=max([r["need"] for r in R.values() if r["key"] == "water"] or [0]),
                dust_need=max([r["need"] for r in R.values() if r["key"] == "dust"] or [0]),
                outdoor=factor_state(env, "outdoor")[0] == "present" or factor_state(env, "uv")[0] == "present",
                flame_need=max([r["need"] for r in R.values() if r["key"] == "flame"] or [0]))


# ---------------- rule-based text assistant (suggestions only) -----------------
KEYWORDS = [
    (r"olej\w* chłodz|cutting oil|coolant oil", "oil_cutting"), (r"emulsj|emulsion|coolant|chłodziw", "emulsion"),
    (r"olej\w* hydrauli|hydraulic", "oil_hydraulic"), (r"olej|\boil", "oil_industrial"), (r"smar|grease", "grease"),
    (r"rozpuszczal|solvent|aceton|alkohol izopropy", "solvents"), (r"detergent", "detergents"), (r"dezynfek|disinfect", "disinfectants"),
    (r"kwas|acid", "acids"), (r"zasad|ług|alkali|caustic", "alkalis"), (r"paliw|benzyn|diesel|fuel|petrol", "fuels"),
    (r"pył metal|metal dust", "dust_metal"), (r"pył drzew|wood dust", "dust_wood"), (r"pył tworzyw|plastic dust", "dust_plastic"),
    (r"pył|dust", "dust_industrial"), (r"wiór|opiłk|chips|swarf", "metal_chips"), (r"odprysk|spatter", "spatter"),
    (r"iskr|spark", "sparks"), (r"spawan|spawal|weld", "spatter"), (r"ścier|abras", "abrasion"), (r"uderz|impact", "impact"),
    (r"przebi|puncture", "puncture"), (r"mycie ciśnien|pressure wash|karcher|hydrodynam", "pressure_wash"),
    (r"strumie\w* wod|water jet", "water_jets"), (r"zachlap|splash", "splash"), (r"para wodna|\bpara\b|steam", "steam"),
    (r"skropl|kondensac|condens", "condensation"), (r"\buv\b|słońc|sun", "uv"), (r"na zewnątrz|outdoor|zewnętrzn", "outdoor"),
    (r"chłodni|cold room|freezer|zamrażaln", "cold_room"), (r"piec|furnace|kiln", "near_furnace"), (r"gorąc\w* element|hot part", "hot_contact"),
    (r"antystat|antistatic", "antistatic"), (r"\besd\b", "esd"), (r"trudnopal|flame|ogniood", "flame_retardant"),
    (r"wodoodporn|waterproof", "waterproof"), (r"pyłoszczeln|dust.?tight", "dust_tight"), (r"przeci[eę]|cut resist", "cut_resistance"),
    (r"bakter|grzyb|mikrob|antimicrob", "antimicrobial"), (r"łatwe czyszcz|easy clean|myć", "easy_cleaning"),
]
LEVEL_WORDS = [(r"ciągł|continuous|non-?stop|stale", 3), (r"regularn|często|codzien|regular|daily|often", 2), (r"sporad|rzadko|occasion|rarely", 1),
               (r"silne|wysok|intensyw|heavy|high|severe", 3), (r"niskie|lekk|low|light", 1)]


def assist_text(text):
    """Map a free-text description to *suggested* factor settings. The user must confirm each one."""
    out, seen = [], set()
    low = (text or "").lower()
    for sentence in re.split(r"[.;\n]+", low):
        for pat, key in KEYWORDS:
            if key == "oil_industrial" and ("oil_cutting" in seen or "oil_hydraulic" in seen):
                continue
            if re.search(pat, sentence) and key not in seen:
                seen.add(key)
                lvl, conf = 2, "low"
                for lp, lv in LEVEL_WORDS:
                    if re.search(lp, sentence):
                        lvl, conf = lv, "medium"
                        break
                f = FACTOR_BY_KEY[key]
                out.append(dict(key=key, level=lvl, confidence=conf, label=f["label"],
                                evidence=sentence.strip()[:120],
                                note=L("Sugestia z analizy tekstu — wymaga potwierdzenia przez użytkownika.",
                                       "Suggestion from text analysis - requires user confirmation.")))
    return out
