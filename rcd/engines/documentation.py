"""Documentation module: builds production documentation (sections A-F + validation) as language-resolved blocks."""
import datetime
from ..i18n import tr
from .environment import FACTOR_BY_KEY, LEVEL_LABELS, RATING_LABEL

STATUS = {"green": ("ZIELONY", "GREEN"), "yellow": ("ŻÓŁTY", "YELLOW"), "red": ("CZERWONY", "RED")}


def build(project, res, lang="pl"):
    pl = lang == "pl"
    T = lambda x: tr(x, lang)
    P = lambda a, b: a if pl else b
    rob, env, reqs = project["robot"], project["environment"], project.get("requirements", {})
    rec = res["material"]["recommended"]
    plan, built, calc, sw = res["construction"], res["pattern"], res["consumption"], res["sewing"]
    eff = rec["effective"]
    secs = []
    # ---- A
    present = []
    for k, f in (env.get("factors") or {}).items():
        if f.get("state") == "present" and k in FACTOR_BY_KEY:
            fd = FACTOR_BY_KEY[k]
            present.append(f"{T(fd['label'])} ({T(LEVEL_LABELS[fd['kind']][int(f.get('level') or 2) - 1])})")
    unknown = res["environment"]["pack"]["critical_unresolved"]
    A = [dict(t="table", head=[P("Parametr", "Parameter"), P("Wartość", "Value")], rows=[
        [P("Projekt", "Project"), project["name"]], [P("Robot", "Robot"), f"{rob.get('manufacturer', '')} {rob.get('model', '')} {rob.get('version', '') or ''}".strip()],
        [P("Typ / osie", "Type / axes"), f"{rob.get('type', '')} / {rob.get('axes', '')}"], [P("Przeznaczenie pokrowca", "Cover purpose"), rob.get("application", "") or "-"],
        [P("Zakres temperatur", "Temperature range"), f"{env.get('tmin_c')} … {env.get('tmax_c')} °C" + (f"; {P('powierzchnia robota', 'robot surface')} {env.get('tsurface_c')} °C" if env.get("tsurface_c") not in (None, "") else "")],
        [P("Występujące czynniki", "Present factors"), "; ".join(present) or "-"],
        [P("Czynniki nierozstrzygnięte (krytyczne)", "Unresolved factors (critical)"), str(len(unknown))],
        [P("Materiał główny", "Main material"), T(rec["name"]) + (f" — {rec['product']}" if rec.get("product") else "")],
        [P("Konstrukcja", "Construction"), f"{plan['style']}; {len(plan['modules'])} {P('modułów', 'modules')}; {len(built['pieces'])} {P('elementów wykroju', 'pattern pieces')}"],
        [P("Zakup materiału", "Material purchase"), f"{calc['buy_m']:.1f} mb × {calc['roll_width_mm']:.0f} mm"],
        [P("Status walidacji", "Validation status"), "R:{red} Y:{yellow} G:{green}".format(**res["validation"]["summary"]) + (P(" — ZATWIERDZONY", " - APPROVED") if project.get("status") == "approved" else P(" — NIEZATWIERDZONY", " - NOT APPROVED"))]])]
    A.append(dict(t="warn", text=P("Pokrowiec jest dodatkowym wyposażeniem maszyny: wymaga oceny ryzyka i walidacji na rzeczywistym stanowisku. Dokument nie deklaruje zgodności z żadnymi normami.",
                                   "The cover is additional machine equipment: it requires risk assessment and validation on the real cell. This document makes no standards-compliance claims.")))
    secs.append(dict(id="A", title=P("A. Karta projektu", "A. Project card"), blocks=A))
    # ---- B
    th, st = sw["thread"], sw["stitch"]
    rows = [[P("Materiał główny", "Main material"), T(rec["name"]), f"{rec['gsm'][0]}–{rec['gsm'][1]} g/m² / {rec['thickness_mm'][0]}–{rec['thickness_mm'][1]} mm ({P('typowo', 'typical')})" if not eff["gsm_confirmed"] else f"{eff['gsm']} g/m² / {eff['thickness_mm']} mm ({P('potwierdzone', 'confirmed')})",
             T(rec["source"]) + f" [{rec['confidence']}]"],
            [P("Nić", "Thread"), T(th["thread"]["name"]), f"Tex {th['tex']} (≈Nm {th['nm_approx']})", T(th["thread"]["source"]) + f" [{th['thread']['confidence']}]"],
            [P("Igła", "Needle"), f"Nm {th['needle_nm'][0]}–{th['needle_nm'][1]}", T(st["needle_point"]), T(st["needle_system"])]]
    for it in res["bom"]:
        if it["category"] == "accessory":
            rows.append([P("Dodatek", "Accessory"), T(it["name"]), f"{it['qty']} {it['unit']}", T(it["spec"]) + (f" [{it['confidence']}]" if it.get("confidence") else "")])
    B = [dict(t="table", head=[P("Pozycja", "Item"), P("Nazwa/typ", "Name/type"), P("Parametry", "Parameters"), P("Źródło / uwagi", "Source / notes")], rows=rows),
         dict(t="p", text=T(rec["justification"])),
         dict(t="p", text=P("Ograniczenia materiału: ", "Material limitations: ") + T(rec["limitations"])),
         dict(t="p", text=P("Wymaga dodatkowych testów: ", "Requires additional tests: ") + (P("TAK", "YES") if rec["requires_tests"] else P("nie", "no")))]
    for w in res["material"]["warnings"]:
        B.append(dict(t="warn", text=T(w)))
    secs.append(dict(id="B", title=P("B. Specyfikacja materiałowa", "B. Material specification"), blocks=B))
    # ---- C
    prow = []
    for p in built["pieces"]:
        f = p["finished"]
        if f["shape"] == "rect":
            fin = f"{f['width']:.0f} × {f['length']:.0f}"
        elif f["shape"] == "sector":
            fin = f"R{f['R_outer']:.0f}/R{f['R_inner']:.0f}, {f['angle_deg']:.1f}°"
        else:
            fin = f"{f['width_start']:.0f}/{f['width_end']:.0f} × {f['length']:.0f}"
        a = p["allowances"]
        prow.append([p["no"], p["id"], T(p["name"]), p["module"], fin, f"{p['bbox'][0]:.0f} × {p['bbox'][1]:.0f}",
                     f"L{a['left']:.0f} R{a['right']:.0f} S{a['start']:.0f} E{a['end']:.0f}", f"{p['area_m2']:.3f}"])
    C = [dict(t="table", head=["Nr", "ID", P("Element", "Piece"), P("Moduł", "Module"), P("Gotowy [mm]", "Finished [mm]"), P("Wykrój bbox [mm]", "Cut bbox [mm]"), P("Zapasy [mm]", "Allowances [mm]"), "m²"], rows=prow),
         dict(t="p", text=P(f"Tolerancja wykonania wykrojów: ±{sw['seam']['tolerance_mm']:.0f} mm. Zapas szwu {sw['seam']['allowance']:.0f} mm, rąbek {sw['seam']['hem']:.0f} mm. Kierunek osnowy wzdłuż osi Y wykroju (strzałka). Skala kontrolna 100×100 mm na wydruku.",
                            f"Cutting tolerance: ±{sw['seam']['tolerance_mm']:.0f} mm. Seam allowance {sw['seam']['allowance']:.0f} mm, hem {sw['seam']['hem']:.0f} mm. Warp direction along the piece Y axis (arrow). 100x100 mm control square on the print.")),
         dict(t="table", head=[P("Parametr", "Parameter"), P("Wynik", "Result")], rows=[
             [P("Szerokość materiału", "Material width"), f"{calc['roll_width_mm']:.0f} mm"], [P("Łączna powierzchnia wykrojów", "Total pattern area"), f"{calc['area_m2']:.3f} m²"],
             [P("Szacowana długość materiału", "Estimated material length"), f"{calc['marker_length_m']:.2f} mb"], [P("Straty materiałowe", "Material waste"), f"{calc['waste_pct']:.1f} %"],
             [P("Zalecany zakup", "Recommended purchase"), f"{calc['buy_m']:.1f} mb"], [P("Dodatkowy zapas", "Additional reserve"), f"{calc['reserve_pct']:.0f} %"]]),
         dict(t="p", text=T(calc["note"]))]
    secs.append(dict(id="C", title=P("C. Dokumentacja wykroju", "C. Pattern documentation"), blocks=C))
    # ---- D
    sec_by = {s["id"]: s for s in plan["sections"]}
    mach = sw["machine"]
    m = mach["machine"]
    steps = [
        P("Przygotowanie materiału: sprawdź belę pod kątem wad, wskaż kierunek osnowy. Jeżeli skurcz/rozciągliwość nie są potwierdzone (patrz B), zmierz je na próbce przed cięciem i skoryguj wykroje.",
          "Material preparation: inspect the roll for defects, identify warp direction. If shrinkage/stretch are unconfirmed (see B), measure them on a sample before cutting and correct the patterns."),
        P(f"Rozłożenie wykrojów: według pliku DXF / mapy rozmieszczenia, szerokość beli {calc['roll_width_mm']:.0f} mm, strzałki osnowy wzdłuż beli, bez obrotu" + ("" if not reqs.get("allow_rotate_90") else " (dopuszczono obrót 90°)") + f". Najpierw sprawdź skalę kontrolną 100×100 mm na wydruku.",
          f"Lay-out: per the DXF / marker map, roll width {calc['roll_width_mm']:.0f} mm, warp arrows along the roll, no rotation" + ("" if not reqs.get("allow_rotate_90") else " (90 deg rotation allowed)") + ". First verify the 100x100 mm control square on the print."),
        P("Wycinanie: dokładnie po linii cięcia (tolerancja ±3 mm). Krawędzie powłok termoplastycznych można zgrzać nożem termicznym; materiały pruące się (aramid, szkło, PTFE-szkło) ciąć ostrymi nożycami/nożem rotacyjnym i zabezpieczyć krawędzie.",
          "Cutting: exactly on the cut line (tolerance +/-3 mm). Thermoplastic coating edges may be sealed with a hot knife; fraying materials (aramid, glass, PTFE-glass) are cut with sharp shears/rotary cutter and edges secured."),
        P("Oznaczenie elementów: numery i ID, nacięcia (karby) 6 mm, linie szycia, linie zakładek/plis, położenie zamków, rzepów i otworów.", "Marking: numbers and IDs, 6 mm notches, sew lines, overlap/pleat lines, zipper, hook-and-loop and opening positions."),
        P("Wzmocnienia: przyszyj łaty R… w miejscu otworów, wytnij otwór po przyszyciu i obszyj krawędź (lamówka).", "Reinforcements: sew patches R... at the openings, cut the hole after sewing and bind the edge."),
        P("Zamki i zapięcia: przyszyj taśmy zamków/rzepów do oznaczonych krawędzi przed łączeniem elementów (elementy leżą płasko); ryglować końce zamków.", "Zippers and closures: sew zipper/hook-and-loop tapes to the marked edges before joining pieces (pieces lie flat); bar-tack the zipper ends."),
    ]
    order = []
    for mod in plan["modules"]:
        names = ", ".join(f"{s} ({T(sec_by[s]['name']) if isinstance(sec_by[s]['name'], dict) else sec_by[s]['name']})" for s in mod["sections"])
        order.append(P(f"{mod['id']}: ", f"{mod['id']}: ") + names)
    steps.append(P("Kolejność łączenia (moduły): ", "Joining order (modules): ") + " | ".join(order) +
                 P(". W obrębie modułu: szwy panelowe → plisowanie sekcji harmonijkowych (G/D wg oznaczeń) → połączenie sekcji szwami → rąbki i kanały ściągaczy.",
                   ". Within a module: panel seams -> pleating of bellows sections (M/V marks) -> join sections by seams -> hems and cinch channels."))
    steps.append(P(f"Szycie: nić {T(th['thread']['name'])} Tex {th['tex']}, igła Nm {th['needle_nm'][0]}–{th['needle_nm'][1]}, ścieg 301 dł. {st['stitch_length_mm']:g} mm, 2 rzędy co 6 mm; maszyna: {T(m['name']) if m else 'brak'}; prędkość start ≤ {mach['settings']['speed_spm']} ściegów/min. {T(mach['settings']['thread_tension'])}. {T(mach['settings']['foot_pressure'])}. OBOWIĄZKOWO wykonaj próbę technologiczną na odpadach materiału (te same warstwy co w szwie krytycznym, {mach['layers']} warstw) i sprawdź symetrię ściegu, brak marszczenia i przebić powłoki.",
                   f"Sewing: thread {T(th['thread']['name'])} Tex {th['tex']}, needle Nm {th['needle_nm'][0]}-{th['needle_nm'][1]}, stitch 301 length {st['stitch_length_mm']:g} mm, 2 rows 6 mm apart; machine: {T(m['name']) if m else 'n/a'}; start speed <= {mach['settings']['speed_spm']} spm. {T(mach['settings']['thread_tension'])}. {T(mach['settings']['foot_pressure'])}. A technological trial on offcuts (same layers as the critical seam, {mach['layers']} layers) is MANDATORY: check stitch symmetry, no puckering and no coating perforation."))
    sealtxt = T(sw["seam"]["seal"]["text"]) if sw["seam"].get("seal") else P("nie wymagane przez wymagania szczelności", "not required by the tightness requirements")
    steps.append(P(f"Wykończenie szwów: obetnij końce nici, uszczelnienie szwów — {sealtxt}; sprawdź krawędzie pod kątem strzępienia.", f"Seam finishing: trim thread ends, seam sealing - {sealtxt}; inspect edges for fraying."))
    steps.append(P("Montaż na robocie: od podstawy do końcówki; moduł dalszy nakłada się na bliższy (zakładka 60 mm); zamknij zapięcia, dociągnij ściągacze tak, by nie zasłaniać wlotów chłodzenia, czujników, elementów bezpieczeństwa i nie naprężać przewodów; po montażu wykonaj ruch próbny z obniżoną prędkością w pełnym zakresie osi.",
                   "Mounting on the robot: from base to tip; the distal module overlaps the proximal one (60 mm skirt); close the closures, tighten cinches without covering cooling inlets, sensors or safety elements and without straining cables; after fitting run a reduced-speed test move over the full axis ranges."))
    steps.append(P("Kontrola jakości: wg sekcji E.", "Quality control: per section E."))
    secs.append(dict(id="D", title=P("D. Instrukcja wykonania", "D. Production instructions"), blocks=[dict(t="ol", items=steps)]))
    # ---- E
    qc = [[P("Zgodność wymiarowa", "Dimensional conformity"), P("wymiary elementów wg tabeli C", "piece dimensions per table C"), "±3 mm", P("miarka / szablon", "tape / template")],
          [P("Jakość szwów", "Seam quality"), P(f"ścieg {st['stitch_length_mm']:g} mm, bez przeskoków, marszczeń i przebić powłoki", f"stitch {st['stitch_length_mm']:g} mm, no skipped stitches, puckering or coating perforation"), P("wizualnie 100%", "visual 100%"), P("oględziny", "inspection")],
          [P("Odporność połączeń", "Joint strength"), P("próba rozrywania szwu na próbce z tych samych warstw — wartość akceptacji ustala odbiorca/konstruktor", "seam pull test on a sample with the same layers - acceptance value set by the customer/engineer"), "-", P("próba zrywania", "pull test")],
          [P("Poprawność mocowania", "Fastening"), P("zamki, rzepy, zatrzaski i ściągacze działają; ryglowanie końców zamków", "zippers, hook-and-loop, snaps and cinches work; zipper ends bar-tacked"), "100%", P("próba funkcji", "function test")],
          [P("Brak kolizji z robotem", "No collision with robot"), P("brak zahaczania o wystające elementy, przewody i złącza", "no snagging on protrusions, cables, connectors"), "-", P("ruch próbny", "test motion")],
          [P("Swoboda ruchów", "Freedom of motion"), P("pełny zakres każdej osi bez oporu i napinania", "full range of each axis without resistance or tension"), "-", P("ruch próbny", "test motion")],
          [P("Brak nadmiernego naprężenia", "No excessive tension"), P("brak naprężonych fałd/szwów w skrajnych położeniach", "no taut folds/seams at extreme poses"), "-", P("oględziny w skrajnych pozycjach", "inspection at extreme poses")],
          [P("Brak kontaktu z gorącymi elementami", "No contact with hot parts"), P("odstęp od gorących powierzchni ≥ luz projektowy", "clearance to hot surfaces >= design clearance"), "-", P("pomiar / termometr", "measurement / thermometer")],
          [P("Możliwość demontażu", "Removability"), P("zdjęcie i założenie każdego modułu bez narzędzi specjalnych", "each module can be removed and refitted without special tools"), "-", P("próba", "trial")],
          [P("Kontrola po testach ruchowych", "Post-motion inspection"), P("po okresie próbnym: ślady tarcia, luzowanie szwów, deformacje plis", "after the trial period: abrasion marks, loose seams, pleat deformation"), "-", P("oględziny", "inspection")]]
    secs.append(dict(id="E", title=P("E. Instrukcja kontroli jakości", "E. Quality control instruction"),
                     blocks=[dict(t="table", head=[P("Kontrola", "Check"), P("Kryterium", "Criterion"), P("Tolerancja", "Tolerance"), P("Metoda", "Method")], rows=qc)]))
    # ---- F
    frows = [[i + 1, T(it["name"]), it["qty"], it["unit"], T(it["spec"]), T(it["why"])] for i, it in enumerate(res["bom"])]
    secs.append(dict(id="F", title=P("F. Lista zakupowa", "F. Purchase list"), blocks=[dict(t="table", head=["#", P("Pozycja", "Item"), P("Ilość", "Qty"), P("Jedn.", "Unit"), P("Specyfikacja", "Specification"), P("Uzasadnienie", "Reason")], rows=frows)]))
    # ---- validation
    vrows = [[T(c["label"]), STATUS[c["status"]][0 if pl else 1], T(c["detail"]), T(c["basis"])] for c in res["validation"]["checks"]]
    secs.append(dict(id="V", title=P("Walidacja", "Validation"), blocks=[dict(t="table", head=[P("Sprawdzenie", "Check"), "Status", P("Szczegóły", "Details"), P("Podstawa", "Basis")], rows=vrows),
                                                                         dict(t="warn", text=P("WIZUALIZACJA w aplikacji jest schematyczna (model uproszczony) — nie jest wymiarowanym modelem CAD ani obrazem produkcyjnym. Dane o statusie 'typowe/niezweryfikowane' wymagają potwierdzenia kartą TDS/SDS.",
                                                                                              "The in-app VISUALISATION is schematic (simplified model) - it is not a dimensioned CAD model nor a production image. Data with 'typical/unverified' status need confirmation by TDS/SDS."))]))
    return dict(title=project["name"], date=datetime.date.today().isoformat(), lang=lang, sections=secs)
