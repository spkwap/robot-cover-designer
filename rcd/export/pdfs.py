import io
import math
from pathlib import Path
from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from xml.sax.saxutils import escape
from ..i18n import tr
from .layout import place_pt, placements_by_no, hole_pts

FD = Path(__file__).resolve().parent.parent / "fonts"
pdfmetrics.registerFont(TTFont("DV", str(FD / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", str(FD / "DejaVuSans-Bold.ttf")))
OVERLAP = 10.0
MARGIN = 10.0


def _draw_piece(c, p, lang):
    c.setLineJoin(1)
    c.setStrokeColor(colors.black); c.setLineWidth(0.5); c.setDash()
    pts = p["cut"]
    path = c.beginPath(); path.moveTo(*pts[0])
    for q in pts[1:]:
        path.lineTo(*q)
    path.close(); c.drawPath(path, stroke=1, fill=0)
    c.setStrokeColor(colors.HexColor("#2a6fdb")); c.setDash(3, 2)
    path = c.beginPath(); path.moveTo(*p["sew"][0])
    for q in p["sew"][1:]:
        path.lineTo(*q)
    path.close(); c.drawPath(path, stroke=1, fill=0)
    c.setStrokeColor(colors.HexColor("#c0392b")); c.setDash([6, 1.5, 1.5, 1.5], 0)
    c.setFont("DV", 3)
    for f in p["folds"]:
        c.line(*f["p"][0], *f["p"][1])
        c.setFillColor(colors.HexColor("#c0392b")); c.drawString(f["p"][0][0] + 2, f["p"][0][1] + 1, tr(f["label"], lang)); 
    c.setDash(); c.setStrokeColor(colors.black); c.setLineWidth(0.8)
    for n in p["notches"]:
        c.line(*n[0], *n[1])
    c.setLineWidth(0.5)
    for h in p["holes"]:
        if h["type"] == "round":
            c.circle(h["cx"], h["cy"], h["d"] / 2, stroke=1, fill=0)
        else:
            c.rect(h["cx"] - h["w"] / 2, h["cy"] - h["h"] / 2, h["w"], h["h"])
        c.setFillColor(colors.black); c.drawString(h["cx"] + 3, h["cy"] + 3, h["label"])
    c.setStrokeColor(colors.HexColor("#1a8f4a")); c.setFillColor(colors.HexColor("#1a8f4a"))
    for m in p["marks"]:
        if m["kind"] == "zipper":
            c.setDash(2, 2); c.setLineWidth(1); c.line(*m["p"][0], *m["p"][1]); c.setDash(); c.setLineWidth(0.5)
        else:
            a, b = m["p"]
            c.rect(min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1]))
        c.setFont("DV", 3); c.drawString(m["p"][0][0] + 2, m["p"][0][1] + 3, tr(m["label"], lang))
    g = p.get("grain")
    c.setStrokeColor(colors.black); c.setFillColor(colors.black)
    if g:
        c.line(g["x"], g["y0"], g["x"], g["y1"]); c.line(g["x"], g["y1"], g["x"] - 3, g["y1"] - 6); c.line(g["x"], g["y1"], g["x"] + 3, g["y1"] - 6)
        c.setFont("DV", 4); c.drawString(g["x"] + 3, (g["y0"] + g["y1"]) / 2, "WARP" if lang == "en" else "OSNOWA")
    c.setFont("DVB", 8); c.drawCentredString(p["bbox"][0] / 2, p["bbox"][1] / 2 + 8, f"#{p['no']}  {p['id']}")
    c.setFont("DV", 4.5); c.drawCentredString(p["bbox"][0] / 2, p["bbox"][1] / 2, tr(p["name"], lang))
    c.drawCentredString(p["bbox"][0] / 2, p["bbox"][1] / 2 - 6, f"{p['bbox'][0]:.0f} x {p['bbox'][1]:.0f} mm")


def pattern_pdf(res, project, lang="pl", sheet="A4"):
    page = A4 if sheet == "A4" else A3
    pw, ph = page[0] / mm - 2 * MARGIN, page[1] / mm - 2 * MARGIN
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page)
    c.setTitle(project["name"])
    P = lambda a, b: a if lang == "pl" else b
    # page 1: print check
    c.setFont("DVB", 14); c.drawString(15 * mm, page[1] - 20 * mm, P("Wykrój pokrowca — skala 1:1", "Cover pattern - 1:1 scale"))
    c.setFont("DV", 9)
    c.drawString(15 * mm, page[1] - 28 * mm, project["name"])
    c.drawString(15 * mm, page[1] - 34 * mm, P("Wydrukuj w skali 100% (bez dopasowania do strony). Sprawdź kwadrat kontrolny linijką:", "Print at 100% (no fit-to-page). Verify the control square with a ruler:"))
    c.setStrokeColor(colors.red); c.setLineWidth(1)
    c.rect(15 * mm, page[1] - 150 * mm, 100 * mm, 100 * mm)
    c.setFont("DV", 10); c.drawString(20 * mm, page[1] - 100 * mm, "100 x 100 mm")
    c.setFillColor(colors.black)
    c.drawString(15 * mm, page[1] - 160 * mm, P(f"Arkusz: {sheet}, zakładka kafelków {OVERLAP:.0f} mm. Kafelki łączyć wg znaczników rejestracji (+) i numerów (kolumna-rząd).", f"Sheet: {sheet}, tile overlap {OVERLAP:.0f} mm. Join tiles using registration marks (+) and numbers (column-row)."))
    c.drawString(15 * mm, page[1] - 168 * mm, P(f"Liczba elementów: {len(res['pattern']['pieces'])}. Zapasy szwów zawarte w liniach cięcia (czarna), linia szycia — niebieska przerywana.", f"Pieces: {len(res['pattern']['pieces'])}. Allowances are included in the cut line (black), sew line - dashed blue."))
    y = page[1] - 180 * mm
    c.setFont("DVB", 8)
    for p in res["pattern"]["pieces"]:
        if y < 20 * mm:
            c.showPage(); y = page[1] - 20 * mm
        nx = max(1, math.ceil((p["bbox"][0] - OVERLAP) / (pw - OVERLAP))); ny = max(1, math.ceil((p["bbox"][1] - OVERLAP) / (ph - OVERLAP)))
        c.setFont("DV", 8); c.drawString(15 * mm, y, f"#{p['no']} {p['id']}  {tr(p['name'], lang)[:60]}  {p['bbox'][0]:.0f} x {p['bbox'][1]:.0f} mm  -> {nx * ny} {P('arkuszy', 'sheets')}")
        y -= 5 * mm
    c.showPage()
    pw0, ph0 = pw, ph
    for p in res["pattern"]["pieces"]:
        W, H = p["bbox"]
        cnt = lambda a, b: max(1, math.ceil((W - OVERLAP) / (a - OVERLAP))) * max(1, math.ceil((H - OVERLAP) / (b - OVERLAP)))
        land = cnt(ph0, pw0) < cnt(pw0, ph0)
        pw, ph = (ph0, pw0) if land else (pw0, ph0)
        page_ = (page[1], page[0]) if land else page
        c.setPageSize(page_)
        nx = max(1, math.ceil((W - OVERLAP) / (pw - OVERLAP))); ny = max(1, math.ceil((H - OVERLAP) / (ph - OVERLAP)))
        for j in range(ny - 1, -1, -1):
            for i in range(nx):
                x0, y0 = i * (pw - OVERLAP), j * (ph - OVERLAP)
                c.saveState()
                c.setFont("DV", 7)
                c.drawString(MARGIN * mm, (MARGIN - 6) * mm if MARGIN > 6 else 2 * mm, f"{project['name'][:45]} | #{p['no']} {p['id']} | {P('kafel', 'tile')} {i + 1}-{j + 1} ({nx}x{ny}) | 1:1 | {P('osnowa ↑', 'warp ↑')}")
                p_ = c.beginPath(); p_.rect(MARGIN * mm, MARGIN * mm, pw * mm, ph * mm); c.clipPath(p_, stroke=0, fill=0)
                c.translate((MARGIN - x0) * mm, (MARGIN - y0) * mm); c.scale(mm, mm)
                _draw_piece(c, p, lang)
                c.restoreState()
                c.saveState(); c.setStrokeColor(colors.grey); c.setLineWidth(0.3); c.setDash(1, 1)
                c.rect(MARGIN * mm, MARGIN * mm, pw * mm, ph * mm)
                for (cx, cy) in ((MARGIN, MARGIN), (MARGIN + pw, MARGIN), (MARGIN, MARGIN + ph), (MARGIN + pw, MARGIN + ph)):
                    c.setDash(); c.line((cx - 4) * mm, cy * mm, (cx + 4) * mm, cy * mm); c.line(cx * mm, (cy - 4) * mm, cx * mm, (cy + 4) * mm)
                c.restoreState()
                c.showPage()
    c.save()
    return buf.getvalue()


def docs_pdf(doc):
    ss = getSampleStyleSheet()
    base = ParagraphStyle("b", parent=ss["Normal"], fontName="DV", fontSize=8.5, leading=11)
    cell = ParagraphStyle("c", parent=base, fontSize=7.2, leading=9)
    h1 = ParagraphStyle("h1", parent=base, fontName="DVB", fontSize=15, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=base, fontName="DVB", fontSize=11, spaceBefore=10, spaceAfter=4)
    warn = ParagraphStyle("w", parent=base, backColor=colors.HexColor("#fff4d6"), borderPadding=4, spaceBefore=4, spaceAfter=4)
    buf = io.BytesIO()
    d = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title=doc["title"])
    story = [Paragraph(escape(doc["title"]), h1), Paragraph(escape(doc["date"]), base)]
    for s in doc["sections"]:
        story.append(Paragraph(escape(s["title"]), h2))
        for b in s["blocks"]:
            if b["t"] == "p":
                story.append(Paragraph(escape(str(b["text"])), base)); story.append(Spacer(1, 3))
            elif b["t"] == "warn":
                story.append(Paragraph("⚠ " + escape(str(b["text"])), warn))
            elif b["t"] == "ol":
                for i, it in enumerate(b["items"], 1):
                    story.append(Paragraph(f"<b>{i}.</b> " + escape(str(it)), base)); story.append(Spacer(1, 2))
            elif b["t"] == "table":
                rows = [[Paragraph(f"<b>{escape(str(x))}</b>", cell) for x in b["head"]]] + [[Paragraph(escape(str(x)), cell) for x in r] for r in b["rows"]]
                n = len(b["head"])
                t = Table(rows, repeatRows=1, colWidths=None)
                t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf7")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                story.append(t); story.append(Spacer(1, 4))
    d.build(story)
    return buf.getvalue()


def bom_csv(items, lang="pl"):
    import csv
    o = io.StringIO()
    w = csv.writer(o, delimiter=";")
    w.writerow(["#", "category", "name", "qty", "unit", "spec", "reason", "confidence"])
    for i, it in enumerate(items, 1):
        w.writerow([i, it["category"], tr(it["name"], lang), it["qty"], it["unit"], tr(it["spec"], lang), tr(it["why"], lang), it.get("confidence") or ""])
    return ("﻿" + o.getvalue()).encode("utf-8")
