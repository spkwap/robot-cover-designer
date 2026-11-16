"""Marker making (nesting) on a fixed-width roll + material consumption calculator.
Pieces are placed by their bounding boxes (MaxRects, bottom-left rule, several orderings, optional 90 deg rotation).
Limitation: curved pieces (cone developments, trapezoids) are nested by bounding box - real nesting of curved
outlines in CAM software can save more material. The result is therefore conservative."""
import math
from ..i18n import L
from .sewing_base import SELVEDGE

GAP = 10.0
END_MARGIN = 25.0
BIG = 1e9


def _split(free, placed):
    px, py, pw, ph = placed
    out = []
    for (fx, fy, fw, fh) in free:
        if px >= fx + fw or px + pw <= fx or py >= fy + fh or py + ph <= fy:
            out.append((fx, fy, fw, fh))
            continue
        if px > fx:
            out.append((fx, fy, px - fx, fh))
        if px + pw < fx + fw:
            out.append((px + pw, fy, fx + fw - px - pw, fh))
        if py > fy:
            out.append((fx, fy, fw, py - fy))
        if py + ph < fy + fh:
            out.append((fx, py + ph, fw, fy + fh - py - ph))
    pruned = []
    for i, a in enumerate(out):
        if a[2] < 1 or a[3] < 1:
            continue
        contained = False
        for j, b in enumerate(out):
            if i != j and a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3] and (a != b or i > j):
                contained = True
                break
        if not contained:
            pruned.append(a)
    return pruned


def _pack(items, strip_w, allow_rot):
    free = [(0.0, 0.0, strip_w + GAP, BIG)]
    placed = []
    for it in items:
        best = None
        for rot in ((0, 90) if allow_rot else (0,)):
            w, h = (it["w"], it["h"]) if rot == 0 else (it["h"], it["w"])
            w, h = w + GAP, h + GAP
            for (fx, fy, fw, fh) in free:
                if w <= fw + 1e-9 and h <= fh + 1e-9:
                    cand = (fy + h, fx, rot, fx, fy, w, h)
                    if best is None or cand < best:
                        best = cand
        if best is None:
            return None
        _, _, rot, x, y, w, h = best
        free = _split(free, (x, y, w, h))
        placed.append(dict(no=it["no"], id=it["id"], x=x, y=y, w=w - GAP, h=h - GAP, rot=rot))
    return placed


def nest(pieces, roll_width, allow_rot=False):
    usable = roll_width - 2 * SELVEDGE
    items = [dict(no=p["no"], id=p["id"], w=p["bbox"][0], h=p["bbox"][1], area=p["area_m2"]) for p in pieces]
    too_wide = [it for it in items if min(it["w"], it["h"] if allow_rot else 1e9) > usable and it["w"] > usable]
    if too_wide:
        return dict(ok=False, error=L(f"Element {too_wide[0]['id']} ({too_wide[0]['w']:.0f} mm) jest szerszy niż użyteczna szerokość beli ({usable:.0f} mm).",
                                      f"Piece {too_wide[0]['id']} ({too_wide[0]['w']:.0f} mm) is wider than the usable roll width ({usable:.0f} mm)."))
    orders = {"area": lambda i: -i["w"] * i["h"], "height": lambda i: (-i["h"], -i["w"]), "width": lambda i: (-i["w"], -i["h"]),
              "longest": lambda i: -max(i["w"], i["h"])}
    best = None
    tried = []
    for name, key in orders.items():
        pl = _pack(sorted(items, key=key), usable, allow_rot)
        if pl is None:
            continue
        length = max(p["y"] + p["h"] for p in pl)
        tried.append((name, round(length)))
        if best is None or length < best[0] - 1e-6:
            best = (length, pl, name)
    if best is None:
        return dict(ok=False, error=L("Nie udało się rozmieścić wykrojów na beli.", "Could not place the pieces on the roll."))
    length, pl, name = best
    for p in pl:
        p["x"] += SELVEDGE
        p["y"] += END_MARGIN
    return dict(ok=True, placements=pl, marker_length_mm=length + 2 * END_MARGIN, strategy=name, tried=tried, usable_width=usable, roll_width=roll_width)


def consumption(pieces, nest_res, reqs, eff, material):
    if not nest_res["ok"]:
        return dict(ok=False, error=nest_res["error"])
    area = sum(p["area_m2"] for p in pieces)
    L_m = nest_res["marker_length_mm"] / 1000.0
    roll_m = nest_res["roll_width"] / 1000.0
    waste = 1 - area / (roll_m * L_m)
    reserve = 5.0 + (0.0 if eff["shrink_confirmed"] else 3.0) + (2.0 if material.get("fray") else 0.0)
    trial = 0.5
    buy = math.ceil(L_m * (1 + reserve / 100) * 10) / 10 + trial
    parts = [dict(label=L("wady/błędy cięcia", "defects/cutting errors"), pct=5.0)]
    if not eff["shrink_confirmed"]:
        parts.append(dict(label=L("niepotwierdzony skurcz/rozciągliwość materiału", "unconfirmed shrinkage/stretch"), pct=3.0))
    if material.get("fray"):
        parts.append(dict(label=L("materiał pruje się — zapas na strzępienie krawędzi", "fraying material - extra for edge loss"), pct=2.0))
    return dict(ok=True, rows=[
        dict(key="width", value=nest_res["roll_width"], unit="mm"), dict(key="area", value=round(area, 3), unit="m²"),
        dict(key="length", value=round(L_m, 3), unit="mb"), dict(key="waste", value=round(waste * 100, 1), unit="%"),
        dict(key="buy", value=round(buy, 1), unit="mb"), dict(key="reserve", value=reserve, unit="%")],
        area_m2=area, marker_length_m=L_m, roll_width_mm=nest_res["roll_width"], waste_pct=waste * 100, reserve_pct=reserve,
        reserve_parts=parts, trial_m=trial, buy_m=buy, strategy=nest_res["strategy"], tried=nest_res["tried"],
        note=L("Przy rozmieszczeniu uwzględniono: marginesy brzegowe beli (15 mm/stronę), odstępy między wykrojami (10 mm), kierunek osnowy (wykroje bez obrotu"
               + ("" if not reqs.get("allow_rotate_90") else ", dopuszczono obrót 90°") + "). Krzywoliniowe wykroje rozmieszczono według prostokątów otaczających (wynik zachowawczy). Zalecany zakup zawiera 0,5 mb na próbę technologiczną.",
               "Placement accounts for roll selvedge (15 mm/side), piece gaps (10 mm), warp direction (no rotation" + ("" if not reqs.get("allow_rotate_90") else ", 90 deg rotation allowed")
               + "). Curved pieces are nested by bounding box (conservative). Recommended purchase includes 0.5 m for the technological trial."))
