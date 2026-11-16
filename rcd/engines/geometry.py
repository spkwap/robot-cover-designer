"""Geometry module: segment normalisation, ease/clearance, circumference, planar kinematics
and a swept clearance check between non-adjacent cover envelopes.

Honest scope: the motion check is a PLANAR approximation (all bend joints assumed coplanar,
segments modelled as capsules). It is a screening tool, not a substitute for a 3D check on the real robot.
"""
import itertools
import math
from ..i18n import L

SHAPES = ("cylinder", "frustum", "box")


def _num(v, default=None):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def normalize_segments(raw):
    """Return (segments, errors). Never invents dimensions: missing mandatory dims -> error."""
    segs, errs = [], []
    for i, s in enumerate(raw or []):
        n = dict(id=s.get("id") or f"S{i + 1}", name=s.get("name") or f"Segment {i + 1}", shape=s.get("shape", "cylinder"),
                 length=_num(s.get("length")), d1=_num(s.get("d1")), d2=_num(s.get("d2")), width=_num(s.get("width")),
                 depth=_num(s.get("depth")), neutral_angle=_num(s.get("neutral_angle"), 0.0), cover=s.get("cover", True) is not False,
                 hot_c=_num(s.get("hot_c")), cooling_vent=bool(s.get("cooling_vent")), service=bool(s.get("service")),
                 closed_end=bool(s.get("closed_end")), protrusions=s.get("protrusions") or ([{"name": "user", "height": _num(s.get("protrusion_h"))}] if _num(s.get("protrusion_h")) else []), openings=s.get("openings") or [],
                 notes=s.get("notes", ""))
        j = s.get("joint_after") or {}
        n["joint_after"] = dict(type=j.get("type", "none"), axis=j.get("axis"), min=_num(j.get("min")), max=_num(j.get("max")),
                                cover_len=_num(j.get("cover_len")))
        if n["shape"] not in SHAPES:
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: nieznany kształt.", f"{n['name']}: unknown shape.")))
        if not n["length"] or n["length"] <= 0:
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: podaj długość segmentu (mm).", f"{n['name']}: provide segment length (mm).")))
        if n["shape"] == "cylinder" and not (n["d1"] and n["d1"] > 0):
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: podaj średnicę (mm).", f"{n['name']}: provide diameter (mm).")))
        if n["shape"] == "frustum" and not (n["d1"] and n["d2"] and n["d1"] > 0 and n["d2"] > 0):
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: stożek wymaga średnic d1 i d2.", f"{n['name']}: frustum needs d1 and d2.")))
        if n["shape"] == "box" and not (n["width"] and n["depth"] and n["width"] > 0 and n["depth"] > 0):
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: prostopadłościan wymaga szerokości i głębokości.", f"{n['name']}: box needs width and depth.")))
        if n["joint_after"]["type"] == "bend" and (n["joint_after"]["min"] is None or n["joint_after"]["max"] is None):
            errs.append(dict(seg=n["id"], text=L(f"{n['name']}: przegub zginany wymaga zakresu ruchu min/max (°).", f"{n['name']}: bending joint needs min/max range (deg).")))
        segs.append(n)
    if not segs:
        errs.append(dict(seg=None, text=L("Brak segmentów robota — wprowadź geometrię (każdy segment osobno) lub zaimportuj model.",
                                          "No robot segments - enter the geometry (each segment separately) or import a model.")))
    return segs, errs


def nominal_dia(s):
    if s["shape"] == "cylinder":
        return s["d1"]
    if s["shape"] == "frustum":
        return max(s["d1"], s["d2"])
    return math.hypot(s["width"], s["depth"])


def ease_mm(s):
    """Radial clearance between robot surface and cover (mm). Base 10; +10 hot surface (>=60 C); +10 cooling vent;
    protrusions: at least protrusion height + 5."""
    c = 10.0
    if s.get("hot_c") is not None and s["hot_c"] >= 60:
        c += 10
    if s.get("cooling_vent"):
        c += 10
    h = max([_num(p.get("height"), 0) for p in s.get("protrusions", [])] or [0])
    return max(c, h + 5) if h else c


def cover_radius(s):
    return nominal_dia(s) / 2 + ease_mm(s)


def circumference(s, t, end=None):
    """Mean-line circumference of the finished cover at a segment end ('start'/'end'/None=mean) in mm."""
    c = ease_mm(s)
    if s["shape"] == "cylinder":
        return math.pi * (s["d1"] + 2 * c + t)
    if s["shape"] == "frustum":
        d = s["d1"] if end in (None, "start") else s["d2"]
        if end is None:
            d = (s["d1"] + s["d2"]) / 2
        return math.pi * (d + 2 * c + t)
    return 2 * (s["width"] + s["depth"]) + 8 * c + 4 * t


def joint_infos(segs):
    """For each covered segment with a bend joint: elongation delta at outer edge etc."""
    info = {}
    for i, s in enumerate(segs):
        j = s["joint_after"]
        if j["type"] != "bend" or i + 1 >= len(segs):
            continue
        a = max(abs(j["min"] or 0), abs(j["max"] or 0))
        r = max(cover_radius(s), cover_radius(segs[i + 1]))
        delta = math.radians(a) * r
        info[i] = dict(index=i, axis=j.get("axis"), half_range_deg=a, radius=r, delta=delta, needs_bellows=delta > 8.0)
    return info


def joint_summary(segs):
    ji = joint_infos(segs)
    return dict(per_joint=ji, needs_bellows=any(v["needs_bellows"] for v in ji.values()),
                has_twist=any(s["joint_after"]["type"] == "twist" for s in segs))


# ---------- planar kinematics ----------
def chain(segs, q):
    x = y = 0.0
    ang = 90.0
    out = []
    for i, s in enumerate(segs):
        ang += s["neutral_angle"] or 0.0
        if i > 0 and segs[i - 1]["joint_after"]["type"] == "bend":
            ang += q.get(i - 1, 0.0)
        x1 = x + s["length"] * math.cos(math.radians(ang))
        y1 = y + s["length"] * math.sin(math.radians(ang))
        out.append(((x, y), (x1, y1), ang))
        x, y = x1, y1
    return out


def _seg_dist(p, q, r, s):
    def sub(a, b): return (a[0] - b[0], a[1] - b[1])
    def dot(a, b): return a[0] * b[0] + a[1] * b[1]
    d1, d2, rr = sub(q, p), sub(s, r), sub(p, r)
    a, e, f = dot(d1, d1), dot(d2, d2), dot(d2, rr)
    if a <= 1e-9 and e <= 1e-9:
        return math.dist(p, r)
    if a <= 1e-9:
        sp, t = 0.0, max(0, min(1, f / e))
    else:
        c = dot(d1, rr)
        if e <= 1e-9:
            t, sp = 0.0, max(0, min(1, -c / a))
        else:
            b = dot(d1, d2)
            den = a * e - b * b
            sp = max(0, min(1, (b * f - c * e) / den)) if den > 1e-9 else 0.0
            t = (b * sp + f) / e
            if t < 0:
                t, sp = 0.0, max(0, min(1, -c / a))
            elif t > 1:
                t, sp = 1.0, max(0, min(1, (b - c) / a))
    c1 = (p[0] + d1[0] * sp, p[1] + d1[1] * sp)
    c2 = (r[0] + d2[0] * t, r[1] + d2[1] * t)
    return math.dist(c1, c2)


def sweep_clearance(segs, max_samples=30000):
    """Minimum gap (mm) between covered, non-adjacent segment envelopes over the joint ranges (planar)."""
    bends = [i for i, s in enumerate(segs) if s["joint_after"]["type"] == "bend" and i + 1 < len(segs)]
    radii = [cover_radius(s) for s in segs]
    cov = [s["cover"] for s in segs]
    steps = 2
    if bends:
        steps = max(3, min(13, int(max_samples ** (1.0 / len(bends)))))
    grids = []
    for i in bends:
        j = segs[i]["joint_after"]
        grids.append([j["min"] + (j["max"] - j["min"]) * k / (steps - 1) for k in range(steps)])
    best = dict(gap=float("inf"), config=None, pair=None)
    n = 0
    combos = itertools.product(*grids) if bends else [()]
    for combo in combos:
        n += 1
        q = {i: a for i, a in zip(bends, combo)}
        ch = chain(segs, q)
        for a in range(len(segs)):
            if not cov[a]:
                continue
            for b in range(a + 2, len(segs)):
                if not cov[b]:
                    continue
                g = _seg_dist(ch[a][0], ch[a][1], ch[b][0], ch[b][1]) - radii[a] - radii[b]
                if g < best["gap"]:
                    best = dict(gap=g, config={f"axis{segs[i]['joint_after'].get('axis') or i + 1}": round(v, 1) for i, v in zip(bends, combo)},
                                pair=(segs[a]["name"], segs[b]["name"]))
    best["samples"] = n
    if best["gap"] == float("inf"):
        best["gap"] = None
    return best


def total_envelope(segs):
    ch = chain(segs, {})
    xs, ys = [], []
    for i, (p, q, _) in enumerate(ch):
        r = cover_radius(segs[i])
        for pt in (p, q):
            xs += [pt[0] - r, pt[0] + r]
            ys += [pt[1] - r, pt[1] + r]
    return dict(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))
