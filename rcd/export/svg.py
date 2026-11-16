from xml.sax.saxutils import escape
from ..i18n import tr
from .layout import place_pt, placements_by_no, hole_pts

COL = dict(cut="#111", sew="#2a6fdb", fold="#c0392b", mark="#1a8f4a", text="#333")


def _path(pts, close=True):
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + (" Z" if close else "")


def piece_group(piece, pl=None, lang="pl", label=True):
    f = (lambda p: place_pt(p, piece, pl)) if pl else (lambda p: p)
    g = [f'<g id="piece-{piece["id"]}">']
    g.append(f'<path d="{_path([f(p) for p in piece["cut"]])}" fill="#eef3fa" fill-opacity="0.5" stroke="{COL["cut"]}" stroke-width="1.2"/>')
    g.append(f'<path d="{_path([f(p) for p in piece["sew"]])}" fill="none" stroke="{COL["sew"]}" stroke-width="0.8" stroke-dasharray="6 3"/>')
    for fo in piece["folds"]:
        a, b = f(fo["p"][0]), f(fo["p"][1])
        g.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{COL["fold"]}" stroke-width="0.6" stroke-dasharray="10 2 2 2"/>')
    for n in piece["notches"]:
        a, b = f(n[0]), f(n[1])
        g.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{COL["cut"]}" stroke-width="1.5"/>')
    for h in piece["holes"]:
        g.append(f'<path d="{_path([f(p) for p in hole_pts(h)])}" fill="#fff" stroke="{COL["cut"]}" stroke-width="1"/>')
    for m in piece["marks"]:
        a, b = f(m["p"][0]), f(m["p"][1])
        if m["kind"] in ("zipper",):
            g.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{COL["mark"]}" stroke-width="2" stroke-dasharray="3 3"/>')
        else:
            x0, y0, x1, y1 = min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])
            g.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" fill="none" stroke="{COL["mark"]}" stroke-width="0.8"/>')
    gr = piece.get("grain")
    if gr:
        a, b = f((gr["x"], gr["y0"])), f((gr["x"], gr["y1"]))
        g.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{COL["text"]}" stroke-width="1" marker-end="url(#arr)"/>')
    if label:
        c = f((piece["bbox"][0] / 2, piece["bbox"][1] / 2))
        g.append(f'<text x="{c[0]:.1f}" y="{c[1]:.1f}" font-size="22" text-anchor="middle" fill="{COL["text"]}" font-family="sans-serif">#{piece["no"]} {escape(piece["id"])}</text>')
        g.append(f'<text x="{c[0]:.1f}" y="{c[1] + 26:.1f}" font-size="14" text-anchor="middle" fill="{COL["text"]}" font-family="sans-serif">{escape(tr(piece["name"], lang))}</text>')
    g.append("</g>")
    return "\n".join(g)


def marker_svg(res, lang="pl"):
    nes = res["nesting"]
    pls = placements_by_no(res)
    W, Hh = nes["roll_width"], nes["marker_length_mm"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 {W + 40} {Hh + 160}" width="100%" font-family="sans-serif">',
           '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#333"/></marker></defs>',
           f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="#fff" stroke="#888" stroke-dasharray="12 6"/>',
           f'<rect x="0" y="0" width="15" height="{Hh}" fill="#ddd"/><rect x="{W - 15}" y="0" width="15" height="{Hh}" fill="#ddd"/>']
    for p in res["pattern"]["pieces"]:
        out.append(piece_group(p, pls[p["no"]], lang))
    cy = Hh + 30
    out.append(f'<rect x="20" y="{cy}" width="100" height="100" fill="none" stroke="#c0392b" stroke-width="1.5"/>')
    out.append(f'<text x="130" y="{cy + 55}" font-size="18" fill="#c0392b">{"Skala kontrolna 100 × 100 mm" if lang == "pl" else "Control square 100 x 100 mm"}</text>')
    out.append(f'<text x="{W / 2}" y="{Hh + 140}" font-size="18" text-anchor="middle" fill="#333">{"Szerokość beli" if lang == "pl" else "Roll width"} {W:.0f} mm — {"długość" if lang == "pl" else "length"} {Hh:.0f} mm</text>')
    out.append("</svg>")
    return "\n".join(out)


def piece_svg(piece, lang="pl"):
    W, H = piece["bbox"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 {W + 40} {H + 40}" width="100%"><defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#333"/></marker></defs>'
            + piece_group(piece, None, lang) + "</svg>")
