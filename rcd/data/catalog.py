"""Technical catalog: materials, threads, machines, accessories, robots.

IMPORTANT - DATA POLICY
-----------------------
No entry below was copied from a specific manufacturer TDS/SDS. Every record carries:
  confidence = "typical"    -> family-level engineering ranges, NOT product-specific data
  confidence = "unverified" -> catalog-level data compiled without access to the original document
  confidence = "verified"   -> only after a user attaches a source (tds_url / document) via the DB editor
The validation engine can return GREEN for a material-dependent requirement ONLY for "verified" records.
Ratings scale: 0 = not resistant, 1 = limited, 2 = good, 3 = excellent, None = unknown.
"""
from ..i18n import L

ACQ = "2026-11-15"
SRC_FAMILY = L("Zakresy typowe dla rodziny materiałowej (opracowanie własne, bez karty TDS konkretnego produktu)",
               "Family-level typical ranges (compiled; no product-specific TDS)")


def chem(mo, cf, so, de, di, ac, al, fu):
    return dict(mineral_oil=mo, cutting_fluid=cf, solvents=so, detergents=de, disinfectants=di,
                acids=ac, alkalis=al, fuels=fu)


def mat(id, pl, en, family, comp, coating, gsm, thick, tmin, tmax, tpeak, ch, abr, tear, cut, punc, flex, flame,
        spark, esd, uv, water, clean, dust, anti, sew, cost, tensile, stretch, fray, crease, hydro, suppliers,
        lim_pl, lim_en, role="main", directional=True, weldable=False, thermoplastic=False):
    return dict(id=id, role=role, name=L(pl, en), family=family, composition=L(*comp), coating=L(*coating),
                gsm=gsm, thickness_mm=thick, tmin_c=tmin, tmax_c=tmax, tpeak_c=tpeak, chem=ch,
                abrasion=abr, tear=tear, cut=cut, puncture=punc, flex=flex, flame=flame, spark=spark, esd=esd,
                uv=uv, water=water, cleanability=clean, dust=dust, antimicrobial=anti, sewability=sew,
                cost_index=cost, tensile_n_50mm=tensile, stretch=stretch, fray=fray, crease_sensitive=crease,
                hydrolysis_risk=hydro, directional=directional, weldable=weldable, thermoplastic_coating=thermoplastic,
                example_suppliers=suppliers, limitations=L(lim_pl, lim_en),
                product=None, tds_url=None, source=SRC_FAMILY, source_date=ACQ, confidence="typical")


MATERIALS = [
    mat("pvc_pes", "Poliester powlekany PVC", "PVC-coated polyester", "pvc_polyester",
        ("poliester (PES) + powłoka PVC", "polyester (PES) + PVC coating"), ("PVC (plastyfikowany)", "PVC (plasticised)"),
        (450, 900), (0.40, 0.80), -30, 70, 90, chem(2, 2, 0, 2, 2, 2, 2, 1), 2, 2, 1, 1, 2, 1, 0, 0, 2, 3, 3, 3, None,
        3, 1, 2500 and (2500, 6000), "low", False, False, False,
        "np. Mehler Texnologies, Heytex, Serge Ferrari, Sioen (sprawdzić dostępność i TDS)",
        "Rozpuszczalniki (keton, aromaty) niszczą PVC; migracja plastyfikatora w kontakcie z olejami/ciepłem; kruchość poniżej ok. -30 °C; wersje FR/antystatyczne to osobne wyroby.",
        "Solvents (ketones, aromatics) attack PVC; plasticiser migration with oils/heat; brittle below approx. -30 °C; FR/antistatic grades are separate products.",
        weldable=True, thermoplastic=True),
    mat("pvc_pes_fr_as", "Poliester powlekany PVC, trudnopalny i antystatyczny", "PVC-coated polyester, flame-retardant antistatic",
        "pvc_polyester",
        ("poliester (PES) + powłoka PVC z dodatkami FR i antystatycznymi", "polyester + PVC with FR and antistatic additives"),
        ("PVC FR/AS", "PVC FR/AS"), (500, 950), (0.45, 0.85), -25, 70, 90, chem(2, 2, 0, 2, 2, 2, 2, 1), 2, 2, 1, 1, 2, 2, 1, 2,
        2, 3, 3, 3, None, 3, 2, (2500, 6000), "low", False, False, False,
        "np. Mehler Texnologies, Heytex (sprawdzić dostępność i TDS)",
        "Jak PVC; deklaracje FR/antystatyczne (norma, rezystancja) muszą wynikać z karty produktu — nie zakładać z rodziny.",
        "As PVC; FR/antistatic claims (standard, resistance) must come from the product datasheet - do not assume from the family.",
        weldable=True, thermoplastic=True),
    mat("pu_pes", "Poliester powlekany poliuretanem (TPU/PU)", "PU/TPU-coated polyester", "pu_polyester",
        ("poliester + powłoka poliuretanowa", "polyester + polyurethane coating"), ("PU / TPU", "PU / TPU"),
        (250, 600), (0.30, 0.60), -30, 90, 110, chem(3, 2, 1, 2, 2, 1, 1, 2), 3, 3, 2, 2, 3, 1, 1, 0, 2, 3, 3, 3, None,
        3, 2, (1500, 4000), "low", False, False, True,
        "np. Sioen, Heytex, producenci laminatów TPU (sprawdzić TDS)",
        "Poliestrowe PU ulega hydrolizie w gorącej wilgotnej atmosferze (emulsje chłodzące, para) — wymagany typ polieterowy lub test; słaba odporność na kwasy/zasady/rozpuszczalniki.",
        "Polyester-type PU hydrolyses in hot humid atmospheres (coolant emulsions, steam) - polyether type or test required; poor to acids/alkalis/solvents.",
        weldable=True, thermoplastic=True),
    mat("pu_pa66", "Poliamid 6.6 (typ Cordura) powlekany PU", "PU-coated polyamide 6.6 (Cordura-type)", "pu_polyamide",
        ("poliamid 6.6 + powłoka PU", "polyamide 6.6 + PU coating"), ("PU", "PU"),
        (250, 550), (0.35, 0.80), -40, 90, 110, chem(2, 2, 1, 2, 1, 0, 2, 1), 3, 3, 2, 2, 3, 0, 1, 0, 1, 3, 2, 3, None,
        3, 1, (1500, 3500), "low", False, False, True,
        "np. Invista (Cordura), Sioen (sprawdzić dostępność i TDS)",
        "Poliamid: kwasy go niszczą, chłonie wodę; nie jest trudnopalny (topi się); UV ogranicza trwałość.",
        "Polyamide: attacked by acids, absorbs water; not flame retardant (melts); UV limits lifetime.",
        weldable=True, thermoplastic=True),
    mat("pa_uncoated", "Tkanina poliamidowa bez powłoki (typ Cordura)", "Uncoated polyamide fabric (Cordura-type)", "polyamide",
        ("poliamid 6.6", "polyamide 6.6"), ("brak", "none"), (200, 450), (0.30, 0.70), -40, 100, 120,
        chem(1, 1, 1, 2, 1, 0, 2, 1), 3, 3, 2, 2, 3, 0, 1, 0, 1, 0, 1, 1, None, 3, 1, (1500, 3000), "low", True, False, False,
        "np. Invista (Cordura) (sprawdzić TDS)",
        "Chłonie oleje i wodę, przepuszcza pył; tylko do suchego, czystego środowiska i ochrony mechanicznej.",
        "Absorbs oils and water, permeable to dust; dry clean environments and mechanical protection only."),
    mat("aramid_unc", "Tkanina aramidowa (Kevlar/Nomex) bez powłoki", "Uncoated aramid fabric (Kevlar/Nomex)", "aramid",
        ("para-/meta-aramid", "para-/meta-aramid"), ("brak", "none"), (200, 450), (0.30, 0.90), -40, 200, 250,
        chem(2, 1, 2, 2, 1, 1, 1, 2), 2, 3, 3, 3, 3, 3, 2, 1, 1, 0, 1, 1, None, 2, 5, (2000, 6000), "low", True, False, False,
        "np. DuPont (Kevlar, Nomex), Teijin (Twaron) (sprawdzić TDS)",
        "Chłonie ciecze (olej, woda), przepuszcza pył; para-aramid degraduje w UV; wysoka cena.",
        "Absorbs liquids (oil, water), permeable to dust; para-aramid degrades in UV; high cost."),
    mat("aramid_sil", "Tkanina aramidowa powlekana silikonem", "Silicone-coated aramid fabric", "aramid_silicone",
        ("aramid + powłoka silikonowa", "aramid + silicone coating"), ("silikon", "silicone"), (250, 600), (0.35, 0.90), -40, 200, 250,
        chem(2, 2, 1, 2, 2, 1, 1, 1), 2, 3, 3, 3, 2, 3, 3, 0, 2, 3, 2, 3, None, 2, 5, (1500, 4000), "low", True, False, False,
        "np. dostawcy tkanin ochronnych dla spawalnictwa/hutnictwa (sprawdzić TDS)",
        "Niska odporność mechaniczna powłoki silikonowej na ścieranie; wysoka cena; powłoka pęcznieje w kontakcie z niektórymi olejami.",
        "Silicone coating has low abrasion resistance; high cost; coating can swell with some oils."),
    mat("silicone_pes", "Poliester powlekany silikonem", "Silicone-coated polyester", "silicone_polyester",
        ("poliester + powłoka silikonowa", "polyester + silicone coating"), ("silikon", "silicone"), (250, 600), (0.25, 0.60), -50, 150, 180,
        chem(1, 2, 0, 2, 3, 1, 1, 0), 1, 2, 1, 1, 3, 2, 2, 0, 3, 3, 3, 3, None, 3, 3, (1000, 2500), "low", True, False, False,
        "np. Heytex, Sioen, producenci tkanin silikonowanych (sprawdzić TDS)",
        "Słaba odporność na ścieranie i rozdarcie; pęcznieje w paliwach i rozpuszczalnikach; trudne uszczelnianie szwów (silikon nie spawa się).",
        "Poor abrasion/tear resistance; swells in fuels and solvents; seam sealing is difficult (silicone cannot be welded)."),
    mat("silicone_glass", "Tkanina szklana powlekana silikonem", "Silicone-coated glass fabric", "silicone_glass",
        ("włókno szklane + silikon", "glass fibre + silicone"), ("silikon", "silicone"), (400, 1200), (0.30, 1.00), -50, 230, 260,
        chem(2, 2, 1, 2, 2, 1, 1, 1), 1, 1, 2, 1, 1, 3, 3, 0, 3, 3, 3, 3, None, 2, 3, (1500, 3000), "low", True, True, False,
        "np. Saint-Gobain, Verseidag, Heinen (sprawdzić TDS)",
        "Włókno szklane łamie się na zagięciach (zmęczenie przy zginaniu), drażni skórę, strzępi się; nie nadaje się do intensywnego zginania.",
        "Glass fibre breaks at folds (flex fatigue), irritates skin, frays; not suitable for heavy flexing."),
    mat("ptfe_glass", "Tkanina szklana powlekana PTFE", "PTFE-coated glass fabric", "ptfe_glass",
        ("włókno szklane + PTFE", "glass fibre + PTFE"), ("PTFE", "PTFE"), (250, 1000), (0.10, 0.80), -70, 260, 280,
        chem(3, 3, 3, 3, 3, 3, 3, 3), 1, 1, 1, 1, 1, 3, 3, 0, 3, 3, 3, 3, None, 1, 5, (1000, 3500), "low", True, True, False,
        "np. Chukoh Chemical, Saint-Gobain (Chemfab), Taconic (sprawdzić TDS)",
        "Łamliwość włókna szklanego na zgięciach, mała odporność na ścieranie, trudne szycie (konieczna nić PTFE/aramid, uszczelnianie szwów), bardzo wysoka cena; wersje antystatyczne tylko według TDS.",
        "Glass fibre fatigue at folds, low abrasion resistance, difficult sewing (PTFE/aramid thread, seam sealing), very high cost; antistatic versions only per TDS."),
    mat("ptfe_lam", "Laminat PTFE na nośniku poliestrowym (wielowarstwowy)", "PTFE-film laminate on polyester carrier (multilayer)",
        "ptfe_laminate", ("folia PTFE + nośnik poliestrowy", "PTFE film + polyester carrier"), ("laminat PTFE", "PTFE laminate"),
        (200, 600), (0.25, 0.70), -50, 150, 180, chem(3, 3, 3, 3, 3, 3, 3, 3), 2, 2, 1, 1, 2, 1, 1, 0, 3, 3, 3, 3, None, 2, 4,
        (1000, 3000), "low", False, False, False,
        "np. producenci laminatów membranowych (sprawdzić TDS)",
        "Folia PTFE może pękać przy wielokrotnym zginaniu; szwy wymagają uszczelnienia; zakres temperatury ogranicza nośnik poliestrowy.",
        "PTFE film may crack under repeated flexing; seams need sealing; polyester carrier limits temperature."),
    mat("pu_pes_esd", "Poliester z PU i siatką przewodzącą (ESD)", "PU-coated polyester with conductive grid (ESD)", "pu_polyester_esd",
        ("poliester + PU + włókna przewodzące", "polyester + PU + conductive fibres"), ("PU", "PU"),
        (250, 600), (0.30, 0.65), -30, 90, 110, chem(3, 2, 1, 2, 2, 1, 1, 2), 3, 3, 2, 2, 3, 1, 1, 3, 2, 3, 3, 3, None, 3, 3,
        (1500, 4000), "low", False, False, True,
        "np. producenci tkanin ESD (sprawdzić TDS i rezystancję)",
        "Skuteczność ESD zależy od uziemienia i rezystancji z karty produktu; hydroliza PU jak w wersji standardowej.",
        "ESD effectiveness depends on grounding and datasheet resistance; PU hydrolysis as standard PU.",
        weldable=True, thermoplastic=True),
    mat("fkm_aramid", "Aramid powlekany fluoroelastomerem (FKM)", "FKM-coated aramid", "fkm_coated",
        ("aramid + powłoka FKM", "aramid + FKM coating"), ("FKM", "FKM"), (350, 900), (0.40, 1.00), -20, 200, 230,
        chem(3, 3, 2, 2, 2, 3, 1, 3), 2, 3, 3, 3, 2, 2, 2, 0, 3, 3, 3, 3, None, 2, 5, (1500, 4000), "low", True, False, False,
        "np. specjalistyczni producenci tkanin powlekanych FKM (sprawdzić TDS)",
        "Słaba odporność na aminy i silne zasady; wysoka cena; ograniczona dostępność małych partii.",
        "Poor to amines and strong alkalis; high cost; limited small-batch availability."),
    mat("cr_pa", "Poliamid powlekany chloroprenem (CR)", "Chloroprene-coated polyamide", "cr_polyamide",
        ("poliamid + powłoka CR", "polyamide + CR coating"), ("CR (chloropren)", "CR (chloroprene)"), (350, 800), (0.50, 1.00), -30, 100, 120,
        chem(3, 3, 1, 2, 2, 2, 2, 2), 3, 3, 2, 2, 2, 2, 1, 0, 2, 3, 3, 3, None, 3, 3, (1500, 3500), "low", True, False, False,
        "np. producenci tkanin gumowanych (sprawdzić TDS)",
        "Powłoka CR nie jest spawalna; szwy wymagają taśmy/kleju; słaba odporność na silne rozpuszczalniki.",
        "CR coating is not weldable; seams need tape/adhesive; poor to strong solvents."),
    mat("aramid_felt", "Filc aramidowy (warstwa termoizolacyjna)", "Aramid needle felt (thermal liner)", "aramid_felt",
        ("meta-aramid, igłowany", "meta-aramid, needle-punched"), ("brak", "none"), (200, 500), (2.0, 4.0), -40, 200, 240,
        chem(1, 1, 2, 1, 1, 1, 1, 1), 1, 1, 1, 1, 1, 3, 2, 0, 1, 0, 1, 1, None, 2, 4, (200, 600), "low", True, False, False,
        "(sprawdzić TDS)", "Chłonie ciecze; wyłącznie warstwa wewnętrzna; wymaga osłony zewnętrznej.",
        "Absorbs liquids; inner layer only; needs an outer protective layer.", role="liner"),
]
for _m in MATERIALS:
    if isinstance(_m["tensile_n_50mm"], tuple):
        pass

# fix a typo-prone field produced by the compact constructor above
for _m in MATERIALS:
    t = _m["tensile_n_50mm"]
    _m["tensile_n_50mm"] = list(t) if isinstance(t, (tuple, list)) else None
    _m["gsm"] = list(_m["gsm"])
    _m["thickness_mm"] = list(_m["thickness_mm"])


def thr(id, pl, en, fibre, ch, flame, uv, abr, tmax, tex, cost, notes_pl, notes_en, strength=2):
    return dict(id=id, name=L(pl, en), fibre=fibre, chem=ch, flame=flame, uv=uv, abrasion=abr, tmax_c=tmax,
                sizes_tex=tex, cost_index=cost, strength_class=strength, notes=L(notes_pl, notes_en),
                product=None, tds_url=None, source=SRC_FAMILY, source_date=ACQ, confidence="typical",
                example_suppliers="np. Amann, Coats, Gütermann (sprawdzić dostępność i TDS)")


THREADS = [
    thr("pet_bonded", "Nić poliestrowa (bonded)", "Bonded polyester thread", "PET",
        chem(2, 2, 2, 2, 2, 2, 1, 2), 0, 3, 2, 120, [40, 70, 90, 135, 210], 1,
        "Uniwersalna do tkanin technicznych; topi się (brak trudnopalności); słaba w mocnych zasadach.",
        "General purpose for technical fabrics; melts (not flame retardant); weak in strong alkalis.", 2),
    thr("pet_corespun", "Nić poliestrowa rdzeniowa (core-spun)", "Core-spun polyester thread", "PET",
        chem(2, 2, 2, 2, 2, 2, 1, 2), 0, 3, 2, 130, [40, 70, 90, 135], 2,
        "Mniejsze nagrzewanie przy szyciu dzięki otoczce; zalecana przy dużych prędkościach.",
        "Lower heat build-up when sewing thanks to the sheath; recommended at higher speeds.", 2),
    thr("pa_bonded", "Nić poliamidowa (bonded)", "Bonded polyamide thread", "PA",
        chem(2, 2, 2, 2, 1, 0, 2, 2), 0, 1, 3, 110, [40, 70, 90, 135, 210], 1,
        "Bardzo dobra odporność na ścieranie; kwasy ją niszczą; słaba w UV.",
        "Very good abrasion resistance; destroyed by acids; poor UV resistance.", 3),
    thr("ptfe", "Nić PTFE", "PTFE thread", "PTFE", chem(3, 3, 3, 3, 3, 3, 3, 3), 3, 3, 1, 260, [70, 90, 135], 5,
        "Odporność chemiczna i temperaturowa; mała odporność na ścieranie i wytrzymałość; stosować z tkaninami PTFE/szklanymi.",
        "Chemical and thermal resistance; low abrasion resistance and strength; use with PTFE/glass fabrics.", 1),
    thr("aramid_meta", "Nić meta-aramidowa (typu Nomex)", "Meta-aramid thread (Nomex-type)", "meta-aramid",
        chem(2, 2, 2, 2, 1, 1, 1, 2), 3, 1, 2, 200, [40, 70, 90, 135], 5,
        "Trudnopalna; ograniczona odporność na UV; do materiałów aramidowych i wysokotemperaturowych.",
        "Flame retardant; limited UV resistance; for aramid and high-temperature materials.", 2),
    thr("aramid_para", "Nić para-aramidowa (typu Kevlar)", "Para-aramid thread (Kevlar-type)", "para-aramid",
        chem(2, 2, 2, 2, 1, 1, 1, 2), 3, 0, 2, 200, [70, 90, 135, 210], 5,
        "Bardzo wysoka wytrzymałość; degraduje w UV (wymaga osłony); trudna do szycia (przecina się na krawędziach igły).",
        "Very high strength; degrades in UV (needs shielding); difficult to sew.", 3),
]


def mach(id, pl, en, mtype, feed, bed, tmax, tex_max, nm_max, throat, min_tube, speed, sub):
    return dict(id=id, name=L(pl, en), type=mtype, feed=feed, bed=bed, max_thickness_mm=tmax, max_tex=tex_max,
                max_needle_nm=nm_max, throat_mm=throat, min_tube_diameter_mm=min_tube, max_speed_spm=speed,
                suitable_for=sub, example_models=[], catalog_ref=None, source=L(
                    "Klasa maszyny - wartości typowe; zweryfikować w katalogu producenta konkretnego modelu",
                    "Machine class - typical values; verify in the manufacturer catalogue of the specific model"),
                source_date=ACQ, confidence="typical")


MACHINES = [
    mach("flat_1n_walking", "Maszyna płaska 1-igłowa, transport złożony (walking foot), stębnówka",
         "Flat-bed single-needle compound-feed lockstitch", "single_needle", "compound", "flat", 8, 90, 130, 250, None, 2500,
         ["standard_tech"]),
    mach("flat_1n_heavy", "Maszyna płaska 1-igłowa do ciężkich materiałów, transport złożony",
         "Heavy-duty flat-bed single-needle compound feed", "single_needle", "compound", "flat", 12, 210, 230, 300, None, 1800,
         ["heavy_tech"]),
    mach("flat_2n_walking", "Maszyna płaska 2-igłowa, transport złożony",
         "Flat-bed two-needle compound feed", "double_needle", "compound", "flat", 8, 135, 160, 250, None, 2000,
         ["standard_tech", "double_row"]),
    mach("post_1n_triple", "Maszyna słupkowa 1-igłowa z potrójnym transportem",
         "Post-bed single-needle triple feed", "single_needle", "triple", "post", 8, 135, 160, 200, 120, 2000,
         ["tubes", "circular_seams"]),
    mach("cyl_1n_triple", "Maszyna ramieniowa (cylinder) 1-igłowa z potrójnym transportem",
         "Cylinder-arm single-needle triple feed", "single_needle", "triple", "cylinder", 8, 135, 160, 150, 60, 1800,
         ["small_tubes", "circular_seams"]),
    mach("weld_hotair", "Zgrzewarka gorącym powietrzem / HF (alternatywa dla szycia, materiały termoplastyczne)",
         "Hot-air / HF welder (alternative to sewing, thermoplastic coatings)", "welding", "roller", "flat", 4, 0, 0, 0, None, 0,
         ["thermoplastic_only"]),
]


def acc(id, cat, pl, en, mat_, size, ch, tmin, tmax, uv, wp, notes_pl, notes_en, cost, flame=None, extra=None):
    d = dict(id=id, category=cat, name=L(pl, en), material=mat_, size=size, chem=ch, tmin_c=tmin, tmax_c=tmax, uv=uv,
             waterproof=wp, flame=flame, cost_index=cost, notes=L(notes_pl, notes_en), product=None, tds_url=None,
             source=L("Typowe właściwości klasy wyrobu, bez karty konkretnego produktu", "Typical class properties, no product-specific datasheet"),
             source_date=ACQ, confidence="typical")
    d.update(extra or {})
    return d


def c4(mo=None, ac_=None, al=None, so=None):
    return dict(mineral_oil=mo, acids=ac_, alkalis=al, solvents=so)


ACCESSORIES = [
    acc("zip_coil_pu", "zipper", "Zamek spiralny nr 8–10 na taśmie z laminatem PU (wodoszczelny)", "Coil zipper #8-#10 on PU-laminated tape (waterproof)",
        "PES + laminat PU", "#8-#10, długość wg listy", c4(2, 1, 1, 1), -30, 80, 2, True,
        "Wodoszczelny; odporność chemiczna ograniczona do klasy laminatu PU; wymaga osłony zakładkowej przy myciu ciśnieniowym.",
        "Waterproof; chemical resistance limited to PU laminate class; needs a storm flap for pressure washing.", 3),
    acc("zip_molded", "zipper", "Zamek z zębami formowanymi (acetal/POM) nr 10", "Moulded-tooth zipper (acetal/POM) #10",
        "taśma PES, zęby POM", "#10", c4(2, 1, 2, 2), -30, 90, 2, False,
        "Odporny mechanicznie; bez właściwości uszczelniających — dodać zakładkę osłonową.", "Mechanically robust; not sealing - add storm flap.", 2),
    acc("zip_steel_hightemp", "zipper", "Zamek z zębami ze stali nierdzewnej na taśmie aramidowej", "Stainless-steel-tooth zipper on aramid tape",
        "stal nierdzewna + taśma aramidowa", "#8-#10", c4(2, 2, 2, 2), -40, 200, 1, False,
        "Do wysokich temperatur i iskier; wysoki koszt; zęby metalowe — ocenić ryzyko ESD/iskrzenia.", "For high temperature and sparks; high cost; metal teeth - assess ESD/sparking risk.", 5, 3),
    acc("hl_pa", "hook_loop", "Rzep przemysłowy PA (haczyki + pętelki)", "Industrial hook-and-loop, PA", "poliamid", "szer. 25 mm", c4(1, 0, 2, 1), -30, 90, 1, False,
        "Standardowy; kwasy go niszczą; chłonie olej (spadek przyczepności).", "Standard; destroyed by acids; oil reduces grip.", 1),
    acc("hl_pp", "hook_loop", "Rzep przemysłowy PP", "Industrial hook-and-loop, PP", "polipropylen", "szer. 25 mm", c4(1, 3, 3, 1), -20, 90, 1, False,
        "Dobra odporność na kwasy/zasady; paliwa i rozpuszczalniki aromatyczne pęczniają PP.", "Good to acids/alkalis; fuels/aromatics swell PP.", 2),
    acc("hl_pps", "hook_loop", "Rzep wysokotemperaturowy PPS", "High-temperature hook-and-loop, PPS", "PPS", "szer. 25 mm", c4(2, 3, 3, 2), -40, 200, 2, False,
        "Do wysokich temperatur i chemii; wysoki koszt; wymaga weryfikacji przyczepności po starzeniu.", "For high temperature and chemicals; high cost; verify grip after ageing.", 5, 3),
    acc("snap_ss", "snap", "Zatrzask zatrzaskowy ze stali nierdzewnej (AISI 304/316)", "Stainless snap fastener (AISI 304/316)",
        "stal nierdzewna", "Ø 15 mm", c4(3, 2, 3, 3), -40, 200, 3, False, "Montaż z podkładkami wzmacniającymi; stal nierdzewna.", "Install with reinforcing washers; stainless steel.", 3, 3),
    acc("buckle_pom", "buckle", "Klamra szybkozłączna (POM) 25 mm", "Quick-release buckle (POM) 25 mm", "POM", "25 mm", c4(3, 1, 2, 2), -30, 80, 1, False,
        "Do pasków zaciskowych na mankietach.", "For cinch straps on cuffs.", 1),
    acc("buckle_ss", "buckle", "Klamra / D-ring ze stali nierdzewnej 25 mm", "Stainless buckle / D-ring 25 mm", "stal nierdzewna", "25 mm", c4(3, 2, 3, 3), -40, 300, 3, False,
        "Do wysokich temperatur.", "For high temperatures.", 3, 3),
    acc("web_pet", "webbing", "Taśma wzmacniająca PES 25 mm", "PES reinforcing webbing 25 mm", "poliester", "25 mm", c4(2, 2, 1, 2), -30, 110, 3, False,
        "Taśma do wzmocnień i pasków.", "Reinforcing tape and straps.", 1, 0),
    acc("web_aramid", "webbing", "Taśma aramidowa 25 mm", "Aramid webbing 25 mm", "aramid", "25 mm", c4(2, 1, 1, 2), -40, 200, 1, False,
        "Trudnopalna; wrażliwa na UV.", "Flame retardant; UV sensitive.", 4, 3),
    acc("bind_pet", "binding", "Lamówka / taśma obszywkowa PES 25 mm", "PES binding tape 25 mm", "poliester", "25 mm", c4(2, 2, 1, 2), -30, 110, 3, False,
        "Obszycie krawędzi tkanin pruących się (otwory, krawędzie).", "Edge binding for fraying fabrics (holes, edges).", 1, 0),
    acc("cord_nbr", "elastic", "Sznur gumowy NBR Ø 6 mm (ściągacz)", "NBR rubber cord Ø 6 mm (cinch)", "NBR", "Ø 6 mm", c4(3, 1, 2, 0), -30, 100, 0, False,
        "Dobra odporność na oleje; słaba w UV/ozonie; słaba na rozpuszczalniki.", "Good oil resistance; poor UV/ozone; poor to solvents.", 2),
    acc("cord_epdm", "elastic", "Sznur gumowy EPDM Ø 6 mm (ściągacz)", "EPDM rubber cord Ø 6 mm (cinch)", "EPDM", "Ø 6 mm", c4(0, 3, 3, 1), -40, 120, 3, False,
        "Dobra odporność na wodę, kwasy, zasady i UV; oleje mineralne go niszczą.", "Good water/acid/alkali/UV; destroyed by mineral oils.", 1),
    acc("cord_silicone", "elastic", "Sznur silikonowy Ø 6 mm (ściągacz)", "Silicone cord Ø 6 mm (cinch)", "silikon", "Ø 6 mm", c4(1, 1, 1, 0), -50, 200, 3, False,
        "Wysoka temperatura; słaba odporność mechaniczna.", "High temperature; low mechanical strength.", 3),
    acc("cord_fkm", "elastic", "Sznur FKM Ø 6 mm (ściągacz)", "FKM cord Ø 6 mm (cinch)", "FKM", "Ø 6 mm", c4(3, 3, 1, 2), -20, 200, 3, False,
        "Chemia i temperatura; wysoki koszt.", "Chemicals and temperature; high cost.", 5),
    acc("tape_tpu", "seam_tape", "Taśma uszczelniająca szwy (termoplastyczna, na gorące powietrze)", "Seam sealing tape (thermoplastic, hot-air)", "TPU/PVC", "szer. 20–25 mm",
        c4(2, 1, 1, 1), -30, 80, 2, True, "Do powłok termoplastycznych (PVC/PU); nie przykleja się do silikonu i PTFE.", "For thermoplastic coatings (PVC/PU); does not bond to silicone and PTFE.", 2),
    acc("sealant_rtv", "seam_tape", "Uszczelniacz silikonowy (RTV) do szwów", "Silicone seam sealant (RTV)", "silikon", "pasta", c4(1, 1, 1, 0), -50, 200, 3, True,
        "Do powłok silikonowych; dobór wg zgodności z TDS.", "For silicone coatings; select per datasheet compatibility.", 2),
    acc("tape_ptfe", "seam_tape", "Taśma uszczelniająca PTFE / FEP (do powłok PTFE)", "PTFE / FEP sealing tape (PTFE coatings)", "PTFE/FEP", "szer. 25 mm",
        c4(3, 3, 3, 3), -70, 260, 3, True, "Do materiałów PTFE; wymaga zgrzewania na gorąco.", "For PTFE materials; requires heat welding.", 5, 3),
    acc("gasket_foam", "gasket", "Uszczelka z pianki zamkniętokomórkowej (zakładka zamka)", "Closed-cell foam gasket (zipper flap)", "EPDM / silikon", "10×3 mm",
        c4(1, 2, 2, 1), -40, 120, 2, True, "Uszczelnienie zakładki osłonowej zamka; dobrać materiał do środowiska.", "Seals zipper storm flap; match material to environment.", 2),
]


def rob(id, mf, model, typ, axes, reach, payload, note=""):
    return dict(id=id, manufacturer=mf, model=model, type=typ, axes=axes, reach_mm=reach, payload_kg=payload,
                segments=None, source=L("Dane katalogowe z pamięci projektantów bazy — wymagają potwierdzenia w dokumentacji producenta; brak wymiarów segmentów",
                                        "Catalogue-level data entered without the original document - verify against manufacturer documentation; no segment dimensions"),
                source_date=ACQ, confidence="unverified", doc_url=None, note=note)


ROBOTS = [
    rob("ur3e", "Universal Robots", "UR3e", "cobot", 6, 500, 3), rob("ur5e", "Universal Robots", "UR5e", "cobot", 6, 850, 5),
    rob("ur10e", "Universal Robots", "UR10e", "cobot", 6, 1300, 12.5), rob("ur16e", "Universal Robots", "UR16e", "cobot", 6, 900, 16),
    rob("fanuc_lrmate200id", "FANUC", "LR Mate 200iD", "articulated", 6, 717, 7),
    rob("fanuc_m20id25", "FANUC", "M-20iD/25", "articulated", 6, 1831, 25),
    rob("abb_irb120", "ABB", "IRB 120", "articulated", 6, 580, 3), rob("abb_irb1200_7", "ABB", "IRB 1200-7/0.7", "articulated", 6, 703, 7),
    rob("kuka_kr6_r900", "KUKA", "KR 6 R900 sixx", "articulated", 6, 901, 6), rob("kuka_kr10_r1100", "KUKA", "KR 10 R1100 sixx", "articulated", 6, 1101, 10),
    rob("yaskawa_gp7", "Yaskawa", "MOTOMAN GP7", "articulated", 6, 927, 7), rob("yaskawa_gp8", "Yaskawa", "MOTOMAN GP8", "articulated", 6, 727, 8),
]
