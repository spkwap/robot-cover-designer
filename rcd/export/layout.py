import math


def place_pt(pt, piece, pl):
    x, y = pt
    if pl["rot"] == 90:
        W, H = piece["bbox"]
        return (pl["x"] + (H - y), pl["y"] + x)
    return (pl["x"] + x, pl["y"] + y)


def placements_by_no(res):
    return {p["no"]: p for p in res["nesting"]["placements"]}


def hole_pts(h, n=36):
    if h["type"] == "round":
        r = h["d"] / 2
        return [(h["cx"] + r * math.cos(2 * math.pi * i / n), h["cy"] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    w, hh = h["w"] / 2, h["h"] / 2
    return [(h["cx"] - w, h["cy"] - hh), (h["cx"] + w, h["cy"] - hh), (h["cx"] + w, h["cy"] + hh), (h["cx"] - w, h["cy"] + hh)]
