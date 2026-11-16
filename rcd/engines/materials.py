"""Material selection module. Deterministic rule evaluation over catalog data.
Returns ONE recommended main material plus transparent reasons for the rejected ones."""
from ..i18n import L
from .environment import CHEM_LABEL, PROP_LABEL, RATING_LABEL

TEMP_MARGIN = 10.0     # K between required continuous temperature and material continuous limit
COLD_MARGIN = 0.0


def _rating(material, r):
    if r["type"] == "chem":
        return material["chem"].get(r["key"])
    if r["type"] == "prop":
        return material.get(r["key"])
    return None


def _label(r):
    return CHEM_LABEL[r["key"]] if r["type"] == "chem" else PROP_LABEL.get(r["key"], L(r["key"]))


def evaluate(material, pack, hot_surface_c=None):
    full = material.get("confidence") == "verified"
    fv = set(material.get("verified_fields") or [])
    isv = lambda k: full or k in fv
    checks, fails, unknowns = [], [], []
    margin = deficit = 0.0
    for r in pack["requirements"]:
        if r["type"] in ("test", "cert"):
            checks.append(dict(req=r["id"], label=L("Wymaga dokumentu/próby", "Requires document/test"), status="test", need=None, rating=None,
                               reason=r["reasons"][0]))
            continue
        rt = _rating(material, r)
        lab = _label(r)
        c = dict(req=r["id"], label=lab, need=r["need"], rating=rt, reason=r["reasons"][0], weight=r["weight"])
        if rt is None:
            c["status"] = "unknown"
            unknowns.append(c)
        elif rt < r["need"]:
            c["status"] = "fail"
            fails.append(c)
            deficit += r["weight"] * (r["need"] - rt)
        else:
            c["status"] = "ok" if isv(("chem." + r["key"]) if r["type"] == "chem" else r["key"]) else "ok_unverified"
            margin += r["weight"] * (0.5 + 0.25 * min(2, rt - r["need"]))
        checks.append(c)
    # temperature
    tmax_req, tmin_req = pack.get("tmax_req"), pack.get("tmin_req")
    if tmax_req is not None:
        ok = material["tmax_c"] >= tmax_req + TEMP_MARGIN
        c = dict(req="temp:max", label=L("temperatura maksymalna (ciągła)", "maximum (continuous) temperature"), need=tmax_req + TEMP_MARGIN,
                 rating=material["tmax_c"], reason=L(f"wymagane {tmax_req:g} °C + margines {TEMP_MARGIN:g} K", f"required {tmax_req:g} C + {TEMP_MARGIN:g} K margin"), weight=5)
        if material["tmax_c"] < tmax_req:
            c["status"] = "fail"; fails.append(c); deficit += 5 * (tmax_req - material["tmax_c"]) / 20 + 5
        elif not ok:
            c["status"] = "marginal"; unknowns.append(c)
        else:
            c["status"] = "ok" if isv("tmax_c") else "ok_unverified"; margin += 2.5
        checks.append(c)
    if pack.get("tpeak") is not None:
        c = dict(req="temp:peak", label=L("temperatura chwilowa (szczytowa)", "short-term peak temperature"), need=pack["tpeak"], rating=material.get("tpeak_c"),
                 reason=L("temperatura szczytowa podana przez użytkownika", "peak temperature given by user"), weight=3)
        if material.get("tpeak_c") is None:
            c["status"] = "unknown"; unknowns.append(c)
        elif material["tpeak_c"] < pack["tpeak"]:
            c["status"] = "fail"; fails.append(c); deficit += 3
        else:
            c["status"] = "ok" if isv("tpeak_c") else "ok_unverified"
        checks.append(c)
    if tmin_req is not None:
        c = dict(req="temp:min", label=L("temperatura minimalna", "minimum temperature"), need=tmin_req, rating=material["tmin_c"],
                 reason=L(f"wymagane {tmin_req:g} °C", f"required {tmin_req:g} C"), weight=4)
        if material["tmin_c"] > tmin_req:
            c["status"] = "fail"; fails.append(c); deficit += 4 + (material["tmin_c"] - tmin_req) / 20
        else:
            c["status"] = "ok" if isv("tmin_c") else "ok_unverified"; margin += 1
        checks.append(c)
    if hot_surface_c is not None:
        c = dict(req="temp:surface", label=L("temperatura powierzchni robota pod pokrowcem", "robot surface temperature under cover"), need=hot_surface_c,
                 rating=material["tmax_c"], reason=L("segment z gorącą powierzchnią", "segment with hot surface"), weight=5)
        if material["tmax_c"] < hot_surface_c:
            c["status"] = "fail"; fails.append(c); deficit += 5
        else:
            c["status"] = "ok" if isv("tmax_c") else "ok_unverified"
        checks.append(c)
    # design-driven exclusions
    if pack.get("no_crease_sensitive") and material.get("crease_sensitive"):
        c = dict(req="design:crease", label=L("zginanie/plisowanie (włókno szklane łamie się na zagięciach)", "folding/pleating (glass fibre breaks at creases)"),
                 need=None, rating=None, status="fail", reason=L("sekcje harmonijkowe", "bellows sections"), weight=5)
        fails.append(c); deficit += 5; checks.append(c)
    if pack.get("hydrolysis_concern") and material.get("hydrolysis_risk"):
        c = dict(req="env:hydrolysis", label=L("ryzyko hydrolizy powłoki PU (gorąco + wilgoć/emulsje)", "PU coating hydrolysis risk (heat + moisture/emulsions)"),
                 need=None, rating=None, status="unknown", reason=L("gorące, wilgotne środowisko", "hot, humid environment"), weight=3)
        unknowns.append(c); checks.append(c)
    verified = full or (not unknowns and all(c["status"] in ("ok", "test", "fail") for c in checks) and any(c["status"] == "ok" for c in checks))
    score = margin - 3 * deficit - 0.6 * len(unknowns) - 0.4 * material["cost_index"] - 0.3 * (3 - material["sewability"])
    return dict(material_id=material["id"], checks=checks, fails=fails, unknowns=unknowns, deficit=deficit, score=score,
                meets_all=not fails, verified=verified)


def _midpoint(rng):
    return round((rng[0] + rng[1]) / 2, 3)


def effective_params(material, confirmed):
    c = dict(confirmed or {})
    vf = set(material.get("verified_fields") or [])
    if "gsm" in vf and c.get("gsm") in (None, ""):
        c["gsm"] = _midpoint(material["gsm"])
    if "thickness_mm" in vf and c.get("thickness_mm") in (None, ""):
        c["thickness_mm"] = _midpoint(material["thickness_mm"])
    out = dict(
        gsm=float(c["gsm"]) if c.get("gsm") not in (None, "") else _midpoint(material["gsm"]),
        gsm_confirmed=c.get("gsm") not in (None, ""),
        thickness_mm=float(c["thickness_mm"]) if c.get("thickness_mm") not in (None, "") else _midpoint(material["thickness_mm"]),
        thickness_max_mm=float(c["thickness_mm"]) if c.get("thickness_mm") not in (None, "") else material["thickness_mm"][1],
        thickness_confirmed=c.get("thickness_mm") not in (None, ""),
        shrink_warp_pct=float(c["shrink_warp_pct"]) if c.get("shrink_warp_pct") not in (None, "") else 0.0,
        shrink_weft_pct=float(c["shrink_weft_pct"]) if c.get("shrink_weft_pct") not in (None, "") else 0.0,
        shrink_confirmed=c.get("shrink_warp_pct") not in (None, "") and c.get("shrink_weft_pct") not in (None, ""),
        product=c.get("product") or material.get("product"), tds_url=c.get("tds_url") or material.get("tds_url"))
    return out


def select(materials, pack, reqs, segs=None):
    mains = [m for m in materials if m.get("role", "main") == "main"]
    hot = max([s["hot_c"] for s in (segs or []) if s.get("hot_c") is not None and s.get("cover")] or [None], default=None) if segs else None
    evals = [(m, evaluate(m, pack, hot)) for m in mains]
    evals.sort(key=lambda me: (not me[1]["meets_all"], me[1]["deficit"], -me[1]["score"], me[0]["id"]))
    override = (reqs or {}).get("material_override")
    chosen = evals[0]
    overridden = False
    if override:
        for me in evals:
            if me[0]["id"] == override:
                chosen, overridden = me, True
    m, ev = chosen
    sat = [c for c in ev["checks"] if c["status"] in ("ok", "ok_unverified")]
    only_unverified = not ev["verified"]
    nver = sum(1 for c in ev["checks"] if c["status"] == "ok_unverified")
    rejected = []
    for mm, e in evals:
        if mm["id"] == m["id"]:
            continue
        reasons = [dict(label=c["label"], need=c["need"], rating=c["rating"]) for c in e["fails"][:3]]
        if not reasons and mm["id"] != m["id"]:
            reasons = [dict(label=L("niższa ocena łączna (koszt, szycie, niewiadome)", "lower overall score (cost, sewability, unknowns)"), need=None, rating=None)]
        rejected.append(dict(id=mm["id"], name=mm["name"], meets_all=e["meets_all"], reasons=reasons))
    eff = effective_params(m, (reqs or {}).get("confirmed"))
    top = sorted(sat, key=lambda c: -(c.get("weight") or 0))[:5]
    why_pl = "; ".join(f"{c['label']['pl']} (wymagane ≥ {RATING_LABEL[c['need']]['pl'] if isinstance(c['need'], int) and c['need'] <= 3 and c['req'][:4] in ('chem', 'prop') else c['need']}, materiał: {RATING_LABEL[c['rating']]['pl'] if isinstance(c['rating'], int) and c['req'][:4] in ('chem', 'prop') else c['rating']})" for c in top)
    why_en = "; ".join(f"{c['label']['en']} (required >= {RATING_LABEL[c['need']]['en'] if isinstance(c['need'], int) and c['need'] <= 3 and c['req'][:4] in ('chem', 'prop') else c['need']}, material: {RATING_LABEL[c['rating']]['en'] if isinstance(c['rating'], int) and c['req'][:4] in ('chem', 'prop') else c['rating']})" for c in top)
    warnings = []
    if not ev["meets_all"]:
        warnings.append(L("ŻADEN materiał z bazy nie spełnia wszystkich wymagań — wybrano rozwiązanie o najmniejszym niedoborze. NIE jest to rozwiązanie bezpieczne bez zmiany wymagań, konstrukcji (np. osłona wielowarstwowa) lub prób.",
                          "NO catalogue material meets all requirements - the least-deficient option was chosen. It is NOT a safe solution without changing requirements, construction (e.g. multilayer shield) or testing."))
    if overridden:
        warnings.append(L("Materiał wybrany ręcznie przez użytkownika (nadpisanie rekomendacji).", "Material chosen manually by the user (override of the recommendation)."))
    if only_unverified:
        warnings.append(L("Dane materiału mają status 'typowe' (rodzina materiałowa) — brak potwierdzenia kartą TDS konkretnego produktu. Parametry traktować jako niezweryfikowane.",
                          "Material data are 'typical' (material family) - not confirmed by a product-specific TDS. Treat parameters as unverified."))
    tests = only_unverified or bool(ev["unknowns"]) or any(c["status"] == "test" for c in ev["checks"]) or bool(pack.get("critical_unresolved"))
    chem_table = [dict(key=k, label=CHEM_LABEL[k], rating=v) for k, v in m["chem"].items()]
    mech = [dict(key=k, label=PROP_LABEL[k], rating=m.get(k)) for k in ("abrasion", "tear", "cut", "puncture", "flex", "uv", "water", "flame", "spark", "esd", "cleanability", "dust")]
    rec = dict(id=m["id"], name=m["name"], product=eff["product"], family=m["family"], example_suppliers=m["example_suppliers"],
               gsm=m["gsm"], thickness_mm=m["thickness_mm"], composition=m["composition"], coating=m["coating"],
               chemical=chem_table, mechanical=mech, tmin_c=m["tmin_c"], tmax_c=m["tmax_c"], tpeak_c=m.get("tpeak_c"),
               tensile_n_50mm=m["tensile_n_50mm"], stretch=m["stretch"], limitations=m["limitations"], fray=m["fray"],
               crease_sensitive=m["crease_sensitive"], thermoplastic_coating=m["thermoplastic_coating"], weldable=m["weldable"],
               directional=m["directional"], sewability=m["sewability"], cost_index=m["cost_index"],
               justification=L("Spełnione wymagania: " + (why_pl or "brak wymagań wiążących") + ".", "Requirements met: " + (why_en or "no binding requirements") + "."),
               source=m["source"], source_date=m["source_date"], confidence=m["confidence"], tds_url=eff["tds_url"],
               requires_tests=tests, verified_all=ev["verified"], verified_fields=m.get("verified_fields") or [], source_document=m.get("source_document"), meets_all=ev["meets_all"], overridden=overridden, checks=ev["checks"],
               effective=eff, fails=[dict(label=c["label"], need=c["need"], rating=c["rating"]) for c in ev["fails"]])
    return dict(recommended=rec, rejected=rejected, warnings=warnings, unresolved=pack["unresolved"],
                critical_unresolved=pack["critical_unresolved"])
