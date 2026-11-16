"""Pattern generator: converts the construction plan into flat pieces with cut line, sew line, allowances,
fold lines, notches, grain direction, closures, openings and reinforcement patches. All dimensions in mm.
Coordinates are piece-local: x across the roll (weft), y along the roll (warp); origin = bottom-left of the cut bbox."""
import math
from ..i18n import L
from . import geometry as G
from .sewing_base import (ZIP_EDGE, VELCRO_OVERLAP, SNAP_OVERLAP, CLOSURE_EDGE_FOLD, SELVEDGE, FLAP_W)


def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _shift(obj, dx, dy):
    if isinstance(obj, tuple) and len(obj) == 2 and not isinstance(obj[0], (list, tuple)):
        return (obj[0] + dx, obj[1] + dy)
    return [_shift(o, dx, dy) for o in obj]


def _scale(obj, sx, sy):
    if isinstance(obj, tuple) and len(obj) == 2 and not isinstance(obj[0], (list, tuple)):
        return (obj[0] * sx, obj[1] * sy)
    return [_scale(o, sx, sy) for o in obj]


def closure_spec(kind, sa, hem_fold):
    """-> (allowance_left, allowance_right, extra_sew_width)."""
    if kind == "zipper":
        return ZIP_EDGE, ZIP_EDGE, 0.0
    if kind == "velcro":
        return CLOSURE_EDGE_FOLD, CLOSURE_EDGE_FOLD, VELCRO_OVERLAP
    if kind == "snaps":
        return CLOSURE_EDGE_FOLD, CLOSURE_EDGE_FOLD, SNAP_OVERLAP
    if kind == "sewn":
        return sa, sa, 0.0
    return CLOSURE_EDGE_FOLD, CLOSURE_EDGE_FOLD, 0.0


class Builder:
    def __init__(self, eff, seam, reqs, material, segs):
        self.eff, self.seam, self.reqs, self.mat, self.segs = eff, seam, reqs, material, segs
        self.t = eff["thickness_mm"]
        self.usable = float(reqs.get("roll_width_mm") or 1500) - 2 * SELVEDGE
        self.sx = 1 + eff["shrink_weft_pct"] / 100.0
        self.sy = 1 + eff["shrink_warp_pct"] / 100.0
        self.pieces, self.seams, self.zippers, self.velcro, self.snaps, self.bindings = [], [], [], [], [], []
        self.warnings = []
        self.sa = seam["allowance"]
        self.hem = seam["hem"]

    # ------------------------------------------------------------------ helpers
    def _add(self, piece):
        sx, sy = self.sx, self.sy
        for key in ("cut", "sew"):
            piece[key] = _scale(piece[key], sx, sy)
        piece["folds"] = [dict(f, p=_scale(f["p"], sx, sy)) for f in piece.get("folds", [])]
        piece["notches"] = _scale(piece.get("notches", []), sx, sy)
        for h in piece.get("holes", []):
            h["cx"] *= sx; h["cy"] *= sy
        for m in piece.get("marks", []):
            m["p"] = _scale(m["p"], sx, sy)
        if piece.get("grain"):
            g = piece["grain"]; g["x"] *= sx; g["y0"] *= sy; g["y1"] *= sy
        x0, y0, x1, y1 = bbox(piece["cut"])
        piece["bbox"] = (x1 - x0, y1 - y0)
        piece["area_m2"] = poly_area(piece["cut"]) / 1e6
        piece["no"] = len(self.pieces) + 1
        self.pieces.append(piece)
        return piece

    def _panels_needed(self, w_sew, al, ar, extra_a=0.0):
        sa = self.sa
        for k in range(1, 25):
            wp = w_sew / k
            if k == 1:
                widest = wp + al + ar
            else:
                widest = wp + max(al + sa, 2 * sa, sa + ar)
            if widest <= self.usable:
                return k
        return 24

    def _rect(self, pid, name, section, kind, w_sew_total, l_sew, al, ar, ab, at, closure, extra_ov=0.0, skirt=0.0, openings=None,
              fold_y=None, note=None):
        k = self._panels_needed(w_sew_total, al, ar)
        sa = self.sa
        out = []
        wp = w_sew_total / k
        for p in range(k):
            a_l = al if p == 0 else sa
            a_r = ar if p == k - 1 else sa
            W, H = wp + a_l + a_r, l_sew + ab + at
            cut = [(0, 0), (W, 0), (W, H), (0, H)]
            sew = [(a_l, ab), (a_l + wp, ab), (a_l + wp, ab + l_sew), (a_l, ab + l_sew)]
            notches = [[(W / 2, 0), (W / 2, 6)], [(W / 2, H), (W / 2, H - 6)], [(0, H / 2), (6, H / 2)], [(W, H / 2), (W - 6, H / 2)]]
            folds = []
            if skirt:
                folds.append(dict(kind="overlap", p=[(a_l, ab + skirt), (a_l + wp, ab + skirt)], label=L("granica zakładki (skirt)", "overlap line (skirt)")))
            marks = []
            if p == 0 and closure == "zipper":
                marks.append(dict(kind="zipper", p=[(a_l, ab + 5), (a_l, ab + l_sew - 5)], label=L("zamek — lewa taśma", "zipper - left tape")))
            if p == k - 1 and closure == "zipper":
                marks.append(dict(kind="zipper", p=[(a_l + wp, ab + 5), (a_l + wp, ab + l_sew - 5)], label=L("zamek — prawa taśma", "zipper - right tape")))
            if p == 0 and closure in ("velcro", "snaps"):
                marks.append(dict(kind="loop" if closure == "velcro" else "snap", p=[(a_l, ab + 10), (a_l + 25, ab + l_sew - 10)],
                                  label=L("rzep — pętelki (wewn.)", "hook&loop - loop (inside)") if closure == "velcro" else L("zatrzaski (część dolna)", "snaps (socket)")))
            if p == k - 1 and closure in ("velcro", "snaps"):
                marks.append(dict(kind="hook" if closure == "velcro" else "snap", p=[(a_l + wp - 25, ab + 10), (a_l + wp, ab + l_sew - 10)],
                                  label=L("rzep — haczyki (zewn.)", "hook&loop - hook (outside)") if closure == "velcro" else L("zatrzaski (część górna)", "snaps (stud)")))
            holes = []
            for o in (openings or []):
                ang = float(o.get("angle_deg") or 0) % 360
                xt = ang / 360.0 * w_sew_total
                if p * wp <= xt < (p + 1) * wp or (p == k - 1 and xt >= (p + 1) * wp):
                    cx, cy = a_l + (xt - p * wp), ab + o["local_pos"]
                    s1 = float(o.get("size1") or 40)
                    s2 = float(o.get("size2") or s1)
                    half = (s1 if o.get("kind", "round") == "round" else s1) / 2
                    if cx - half - 15 < a_l - 1e-6 or cx + half + 15 > a_l + wp + 1e-6:
                        if k > 1 or closure != "none":
                            self.warnings.append(L(f"Otwór '{o.get('name', '')}' leży zbyt blisko krawędzi/szwu/zamka na elemencie {pid} — przesuń kąt położenia.",
                                                   f"Opening '{o.get('name', '')}' is too close to an edge/seam/zipper on piece {pid} - move its angular position."))
                    holes.append(dict(type=o.get("kind", "round"), cx=cx, cy=cy, d=s1, w=s1, h=s2, label=o.get("name", ""), purpose=o.get("type", "cable")))
            piece = dict(id=pid if k == 1 else f"{pid}.{p + 1}", section=section["id"], module=section["module"], name=name, kind=kind,
                         cut=cut, sew=sew, folds=folds, notches=notches, holes=holes, marks=marks,
                         grain=dict(x=W / 2, y0=H * 0.3, y1=H * 0.7),
                         finished=dict(shape="rect", width=wp, length=l_sew), allowances=dict(left=a_l, right=a_r, start=ab, end=at),
                         note=note, panels=k, panel_index=p + 1, closure=closure)
            out.append(self._add(piece))
        # seams
        if k > 1:
            self.seams.append(dict(kind="seam", length=(k - 1) * l_sew, rows=2, layers=2, where=f"{pid} panels"))
        return out

    def _patches(self, section, pieces):
        for pc in pieces:
            for h in pc["holes"]:
                size = (h["d"] if h["type"] == "round" else max(h["w"], h["h"])) + 60
                pid = f"R{len([x for x in self.pieces if x['kind'] == 'patch']) + 1}"
                c = [(0, 0), (size, 0), (size, size), (0, size)]
                s = [(10, 10), (size - 10, 10), (size - 10, size - 10), (10, size - 10)]
                self._add(dict(id=pid, section=section["id"], module=section["module"],
                               name=L(f"Wzmocnienie otworu '{h['label']}' ({pc['id']})", f"Opening patch '{h['label']}' ({pc['id']})"), kind="patch",
                               cut=c, sew=s, folds=[], notches=[], holes=[], marks=[dict(kind="hole", p=[(size / 2, size / 2), (size / 2 + h["d"] / 2, size / 2)],
                                                                                           label=L("otwór do wycięcia po przyszyciu", "hole to cut after sewing"))],
                               grain=dict(x=size / 2, y0=size * 0.3, y1=size * 0.7), finished=dict(shape="rect", width=size - 20, length=size - 20),
                               allowances=dict(left=10, right=10, start=10, end=10), note=None, panels=1, panel_index=1, closure=None))
                per = 4 * (size - 20)
                self.seams.append(dict(kind="patch", length=per, rows=2, layers=3, where=pid))
                self.bindings.append(dict(length=math.pi * (h["d"] if h["type"] == "round" else 2 * (h["w"] + h["h"]) / 2), where=f"{pc['id']} {h['label']}"))

    # ------------------------------------------------------------------ section builders
    def tube_like(self, sc):
        seg = self.segs[sc["seg"]]
        C = G.circumference(seg, self.t)
        al, ar, extra = closure_spec(sc["closure"], self.sa, self.seam["hem_fold"])
        skirt = sc["skirt"]
        l_sew = sc["finished_length"] + skirt
        ab = self.sa if sc["start_finish"] == "seam" else self.hem
        at = self.sa if sc["end_finish"] == "seam" else self.hem
        w_total = C + extra
        kind = "box_wrap" if sc["kind"] == "box" else "tube"
        pcs = self._rect(sc["id"], L(f"{sc['name']} — płaszcz", f"{sc['name']} - body"), sc, kind, w_total, l_sew, al, ar, ab, at, sc["closure"],
                         skirt=skirt, openings=sc.get("openings"))
        self._patches(sc, pcs)
        self._finish_common(sc, w_total, l_sew, C, pcs)
        if sc["kind"] == "box" and seg["closed_end"]:
            w, d = seg["width"] + 2 * G.ease_mm(seg) + self.t, seg["depth"] + 2 * G.ease_mm(seg) + self.t
            cap = self._rect(f"{sc['id']}c", L(f"{sc['name']} — wieko", f"{sc['name']} - cap"), sc, "box_cap", w, d, self.sa, self.sa, self.sa, self.sa, "none")
            self.seams.append(dict(kind="seam", length=2 * (w + d), rows=2, layers=2, where=f"{sc['id']} cap"))
        return pcs

    def _finish_common(self, sc, w_total, l_sew, C, pcs):
        hl = self.seam["hem_fold"]
        layers_hem = 3 if self.seam["hem_double_fold"] else 2
        if sc["start_finish"] in ("hem", "skirt"):
            self.seams.append(dict(kind="hem", length=w_total, rows=1, layers=layers_hem, where=f"{sc['id']} start"))
        if sc["end_finish"] == "hem":
            self.seams.append(dict(kind="hem", length=w_total, rows=1, layers=layers_hem, where=f"{sc['id']} end"))
        cl = sc["closure"]
        if cl == "zipper":
            self.zippers.append(dict(section=sc["id"], module=sc["module"], length=l_sew + 20, flexible=sc["kind"] == "bellows"))
            self.seams.append(dict(kind="zipper", length=2 * l_sew, rows=2, layers=3, where=f"{sc['id']} zipper"))
        elif cl == "velcro":
            self.velcro.append(dict(section=sc["id"], module=sc["module"], length=2 * max(l_sew - 20, 10), width=25))
            self.seams.append(dict(kind="velcro", length=4 * max(l_sew - 20, 10), rows=1, layers=3, where=f"{sc['id']} hook&loop"))
        elif cl == "snaps":
            n = math.ceil(l_sew / 100.0) + 1
            self.snaps.append(dict(section=sc["id"], module=sc["module"], count=n))
        elif cl == "sewn":
            self.seams.append(dict(kind="seam", length=l_sew, rows=2, layers=2, where=f"{sc['id']} longitudinal"))
        elif cl == "none":
            self.seams.append(dict(kind="hem", length=2 * l_sew, rows=1, layers=layers_hem, where=f"{sc['id']} edges"))
        # storm flap
        pack = self.pack
        if cl == "zipper" and (pack.get("waterproof_level", 0) >= 2 or pack.get("dust_need", 0) >= 2):
            f = self._rect(f"{sc['id']}f", L(f"{sc['name']} — zakładka osłonowa zamka", f"{sc['name']} - zipper storm flap"), sc, "flap", FLAP_W, l_sew, 15, 15, 15, 15, "none")
            self.seams.append(dict(kind="seam", length=l_sew, rows=2, layers=3, where=f"{sc['id']} flap"))

    def frustum(self, sc):
        seg = self.segs[sc["seg"]]
        c, t = G.ease_mm(seg), self.t
        r1, r2 = (seg["d1"] + 2 * c + t) / 2, (seg["d2"] + 2 * c + t) / 2
        Lf = sc["finished_length"]
        if sc["skirt"]:
            slope = (r1 - r2) / sc["finished_length"]
            r1 += slope * sc["skirt"]
            Lf += sc["skirt"]
        if abs(r1 - r2) < 1.0:
            self.warnings.append(L(f"Stożek '{sc['name']}' ma prawie równe średnice — wykrój wykonano jako walec.", f"Frustum '{sc['name']}' has nearly equal diameters - patterned as a cylinder."))
            sc2 = dict(sc, kind="tube")
            self.segs = list(self.segs)
            tmp = dict(seg, shape="cylinder", d1=(seg["d1"] + seg["d2"]) / 2)
            self.segs[sc["seg"]] = tmp
            return self.tube_like(sc2)
        big_is_start = r1 > r2
        rb, rs = (r1, r2) if big_is_start else (r2, r1)
        s_len = math.hypot(Lf, rb - rs)
        Rb = s_len * rb / (rb - rs)
        Rs = Rb - s_len
        al, ar, extra = closure_spec(sc["closure"], self.sa, self.seam["hem_fold"])
        phi_total = (2 * math.pi * rb + extra) / Rb
        a_start = self.sa if sc["start_finish"] == "seam" else self.hem
        a_end = self.sa if sc["end_finish"] == "seam" else self.hem
        eb, es = (a_start, a_end) if big_is_start else (a_end, a_start)
        if Rs - es < 5:
            self.warnings.append(L(f"Stożek '{sc['name']}': mały promień rozwinięcia ({Rs:.0f} mm) — zapas wykończenia ograniczony.", f"Frustum '{sc['name']}': small development radius ({Rs:.0f} mm) - finishing allowance limited."))
            es = max(0.0, Rs - 5)
        out = []
        for k in range(1, 25):
            a = phi_total / k
            widths = []
            for p in range(k):
                el = al if p == 0 else self.sa
                er = ar if p == k - 1 else self.sa
                cut, _ = self._sector(Rb, Rs, a, eb, es, el, er)
                x0, y0, x1, y1 = bbox(cut)
                widths.append(x1 - x0)
            if max(widths) <= self.usable:
                break
        for p in range(k):
            el = al if p == 0 else self.sa
            er = ar if p == k - 1 else self.sa
            cut, sew = self._sector(Rb, Rs, a, eb, es, el, er)
            x0, y0, x1, y1 = bbox(cut)
            cut, sew = _shift(cut, -x0, -y0), _shift(sew, -x0, -y0)
            W, H = x1 - x0, y1 - y0
            piece = dict(id=sc["id"] if k == 1 else f"{sc['id']}.{p + 1}", section=sc["id"], module=sc["module"],
                         name=L(f"{sc['name']} — rozwinięcie stożka", f"{sc['name']} - frustum development"), kind="frustum", cut=cut, sew=sew,
                         folds=[], notches=[[(W / 2, 0), (W / 2, 6)], [(W / 2, H), (W / 2, H - 6)]], holes=[], marks=[],
                         grain=dict(x=W / 2, y0=H * 0.3, y1=H * 0.7),
                         finished=dict(shape="sector", R_outer=Rb, R_inner=Rs, angle_deg=math.degrees(a), arc_outer=Rb * a, arc_inner=Rs * a),
                         allowances=dict(left=el, right=er, start=a_start, end=a_end), note=L("Rozwinięcie stożka: kierunek osnowy wzdłuż osi elementu (po skosie na brzegach).", "Cone development: warp along the element axis (bias at edges)."),
                         panels=k, panel_index=p + 1, closure=sc["closure"])
            out.append(self._add(piece))
        if sc.get("openings"):
            self.warnings.append(L(f"Otwory w stożku '{sc['name']}' nie są automatycznie umieszczane na wykroju — wymagają ręcznego dodania.", f"Openings in frustum '{sc['name']}' are not placed automatically - add manually."))
        if k > 1:
            self.seams.append(dict(kind="seam", length=(k - 1) * s_len, rows=2, layers=2, where=f"{sc['id']} panels"))
        self._finish_common(sc, 2 * math.pi * rb + extra, s_len, 2 * math.pi * rb, out)
        return out

    @staticmethod
    def _sector(Ro, Ri, a, eo, ei, el, er):
        def arc(r, t0, t1, n=None):
            n = n or max(8, int(abs(t1 - t0) / math.radians(2)))
            return [(r * math.sin(t0 + (t1 - t0) * i / n), r * math.cos(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]
        Ro2, Ri2 = Ro + eo, max(Ri - ei, 1.0)
        def th(e, r):
            return math.asin(min(1.0, e / r)) if r > 0 else 0.0
        cut = arc(Ro2, -a / 2 - th(el, Ro2), a / 2 + th(er, Ro2)) + arc(Ri2, a / 2 + th(er, Ri2), -a / 2 - th(el, Ri2))
        sew = arc(Ro, -a / 2, a / 2) + arc(Ri, a / 2, -a / 2)
        return cut, sew

    def bellows(self, sc):
        b = sc["bellows"]
        s1, s2 = self.segs[sc["seg"]], self.segs[sc["seg2"]]
        C1, C2 = G.circumference(s1, self.t, "end" if s1["shape"] == "frustum" else None), G.circumference(s2, self.t, "start" if s2["shape"] == "frustum" else None)
        if max(C1, C2) / min(C1, C2) > 1.3:
            self.warnings.append(L(f"Sekcja harmonijkowa '{sc['name']}' łączy przekroje o obwodach różniących się > 30% — kształt trapezowy jest przybliżeniem.",
                                   f"Bellows '{sc['name']}' joins sections whose circumferences differ by > 30% - trapezoid shape is an approximation."))
        al, ar, extra = closure_spec(sc["closure"], self.sa, self.seam["hem_fold"])
        ex = extra
        C1e, C2e = C1 + ex, C2 + ex
        Ld = sc["dev_length"] + sc["skirt"]
        ab = self.sa if sc["start_finish"] == "seam" else self.hem
        at = self.sa if sc["end_finish"] == "seam" else self.hem
        k = self._panels_needed(max(C1e, C2e), al, ar)
        out = []
        for p in range(k):
            a_l = al if p == 0 else self.sa
            a_r = ar if p == k - 1 else self.sa
            def xl(W, f): return -W / 2 + W * f
            lb, rb_, lt, rt = xl(C1e, p / k), xl(C1e, (p + 1) / k), xl(C2e, p / k), xl(C2e, (p + 1) / k)
            cut = [(lb - a_l, -ab), (rb_ + a_r, -ab), (rt + a_r, Ld + at), (lt - a_l, Ld + at)]
            sew = [(lb, 0), (rb_, 0), (rt, Ld), (lt, Ld)]
            x0, y0, x1, y1 = bbox(cut)
            cut, sew = _shift(cut, -x0, -y0), _shift(sew, -x0, -y0)
            ox, oy = -x0, -y0
            folds = []
            h = b["h"]
            f0 = (Ld - b["n"] * 2 * h) / (b["n"] + 1) + sc["skirt"]
            for m in range(1, 2 * b["n"] + 1):
                y = f0 + m * h
                f = y / Ld if Ld else 0
                xa = (lb + (lt - lb) * f) + ox
                xb = (rb_ + (rt - rb_) * f) + ox
                folds.append(dict(kind="mountain" if m % 2 else "valley", p=[(xa, y + oy), (xb, y + oy)],
                                  label=L("grzbiet (G)" if m % 2 else "dolina (D)", "mountain (M)" if m % 2 else "valley (V)")))
            W, H = x1 - x0, y1 - y0
            marks = []
            if sc["closure"] == "velcro" and p == 0:
                marks.append(dict(kind="loop", p=[(a_l, ab + 10), (a_l + 25, ab + Ld - 10)], label=L("rzep — pętelki (wewn.)", "hook&loop - loop (inside)")))
            if sc["closure"] == "velcro" and p == k - 1:
                marks.append(dict(kind="hook", p=[(W - a_r - 25, ab + 10), (W - a_r, ab + Ld - 10)], label=L("rzep — haczyki (zewn.)", "hook&loop - hook (outside)")))
            piece = dict(id=sc["id"] if k == 1 else f"{sc['id']}.{p + 1}", section=sc["id"], module=sc["module"],
                         name=L(f"{sc['name']} — sekcja harmonijkowa (przegub)", f"{sc['name']} - bellows (joint)"), kind="bellows", cut=cut, sew=sew,
                         folds=folds, notches=[[(W / 2, 0), (W / 2, 6)], [(W / 2, H), (W / 2, H - 6)]], holes=[], marks=marks,
                         grain=dict(x=W / 2, y0=H * 0.3, y1=H * 0.7),
                         finished=dict(shape="trapezoid", width_start=(C1e) / k, width_end=(C2e) / k, length=Ld,
                                       pleats=b["n"], pleat_height=h, neutral_length=sc["finished_length"], min_length=b["min_len"]),
                         allowances=dict(left=a_l, right=a_r, start=ab, end=at), note=L(f"{b['n']} plis po {h:g} mm; długość rozwinięta {sc['dev_length']:.0f} mm; zakres pracy {b['min_len']:.0f}…{b['Ld']:.0f} mm.",
                                                                                    f"{b['n']} pleats of {h:g} mm; developed length {sc['dev_length']:.0f} mm; working range {b['min_len']:.0f}...{b['Ld']:.0f} mm."),
                         panels=k, panel_index=p + 1, closure=sc["closure"])
            out.append(self._add(piece))
        if k > 1:
            self.seams.append(dict(kind="seam", length=(k - 1) * Ld, rows=2, layers=2, where=f"{sc['id']} panels"))
        self._finish_common(sc, max(C1e, C2e), Ld, max(C1, C2), out)
        return out


def build(plan, segs, eff, seam, reqs, material, pack):
    B = Builder(eff, seam, reqs, material, segs)
    B.pack = pack
    for sc in plan["sections"]:
        if sc["kind"] in ("tube", "box"):
            B.tube_like(sc)
        elif sc["kind"] == "frustum":
            B.frustum(sc)
        elif sc["kind"] == "bellows":
            B.bellows(sc)
    for j in plan["joins"]:
        sa = B.sa
        if j["type"] == "seam":
            a = next(s for s in plan["sections"] if s["id"] == j["a"])
            seg = segs[a["seg"]]
            B.seams.append(dict(kind="seam", length=G.circumference(seg, B.t), rows=2, layers=2, where=f"{j['a']}+{j['b']}"))
        else:
            B.seams.append(dict(kind="cuff", length=0.0, rows=0, layers=0, where=f"{j['a']}/{j['b']}"))
    return dict(pieces=B.pieces, seams=B.seams, zippers=B.zippers, velcro=B.velcro, snaps=B.snaps, bindings=B.bindings,
                warnings=B.warnings, usable_width=B.usable)
