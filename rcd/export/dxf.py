import io
import ezdxf
from .layout import place_pt, placements_by_no, hole_pts


def marker_dxf(res):
    doc = ezdxf.new("R2010")
    doc.units = 4  # mm
    for name, color in (("CUT", 7), ("SEW", 5), ("FOLD", 1), ("NOTCH", 7), ("GRAIN", 3), ("TEXT", 8), ("HOLES", 2), ("MARKS", 3), ("CONTROL", 1), ("ROLL", 9)):
        doc.layers.add(name, color=color)
    doc.layers.get("SEW").dxf.linetype = "DASHED" if "DASHED" in doc.linetypes else "CONTINUOUS"
    msp = doc.modelspace()
    nes = res["nesting"]
    pls = placements_by_no(res)
    W, Hh = nes["roll_width"], nes["marker_length_mm"]
    msp.add_lwpolyline([(0, 0), (W, 0), (W, Hh), (0, Hh)], close=True, dxfattribs={"layer": "ROLL"})
    for p in res["pattern"]["pieces"]:
        pl = pls[p["no"]]
        f = lambda q: place_pt(q, p, pl)
        msp.add_lwpolyline([f(q) for q in p["cut"]], close=True, dxfattribs={"layer": "CUT"})
        msp.add_lwpolyline([f(q) for q in p["sew"]], close=True, dxfattribs={"layer": "SEW"})
        for fo in p["folds"]:
            msp.add_line(f(fo["p"][0]), f(fo["p"][1]), dxfattribs={"layer": "FOLD"})
        for n in p["notches"]:
            msp.add_line(f(n[0]), f(n[1]), dxfattribs={"layer": "NOTCH"})
        for h in p["holes"]:
            if h["type"] == "round":
                msp.add_circle(f((h["cx"], h["cy"])), h["d"] / 2, dxfattribs={"layer": "HOLES"})
            else:
                msp.add_lwpolyline([f(q) for q in hole_pts(h)], close=True, dxfattribs={"layer": "HOLES"})
        for m in p["marks"]:
            msp.add_line(f(m["p"][0]), f(m["p"][1]), dxfattribs={"layer": "MARKS"})
        g = p.get("grain")
        if g:
            msp.add_line(f((g["x"], g["y0"])), f((g["x"], g["y1"])), dxfattribs={"layer": "GRAIN"})
        c = f((p["bbox"][0] / 2, p["bbox"][1] / 2))
        msp.add_text(f"#{p['no']} {p['id']}", height=18, dxfattribs={"layer": "TEXT", "insert": c})
    msp.add_lwpolyline([(0, -150), (100, -150), (100, -50), (0, -50)], close=True, dxfattribs={"layer": "CONTROL"})
    msp.add_text("CONTROL 100x100 mm", height=10, dxfattribs={"layer": "CONTROL", "insert": (110, -100)})
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode("utf-8")
