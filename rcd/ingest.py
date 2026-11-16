"""Document ingestion: read technical data from an uploaded document (PDF/HTML/TXT) or from a user-supplied URL.

Policy: extraction is rule-based and returns PROPOSALS with the quoted evidence. Nothing is stored in the catalogue until
the user accepts each field; only accepted fields are marked as verified (per-field provenance: verified_fields)."""
import hashlib
import io
import ipaddress
import os
import re
import socket
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from . import db
from .i18n import L

MAX_BYTES = 30 * 1024 * 1024


# ---------------------------------------------------------------- fetching
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def _check_url(url):
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("Only http(s) URLs are allowed.")
    if os.environ.get("RCD_ALLOW_PRIVATE_URLS") == "1":
        return
    for info in socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80)):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("URL points to a private/internal address - blocked (set RCD_ALLOW_PRIVATE_URLS=1 to allow on a trusted host).")


def fetch_url(url, timeout=25):
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(4):
        _check_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": "RobotCoverDesigner/1.0 (technical datasheet import)"})
        try:
            r = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            raise ValueError(f"HTTP {e.code} while fetching the document.")
        except Exception as e:
            raise ValueError(f"Cannot fetch the document: {e}")
        data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Document larger than 30 MB.")
        name = os.path.basename(urllib.parse.urlparse(url).path) or "document"
        return data, r.headers.get("content-type", ""), url, name
    raise ValueError("Too many redirects.")


# ---------------------------------------------------------------- text extraction
def extract_text(name, data, content_type=""):
    low = name.lower()
    if data[:5] == b"%PDF-" or low.endswith(".pdf") or "pdf" in content_type:
        try:
            from pypdf import PdfReader
            txt = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages)
            if txt.strip():
                return txt
        except Exception:
            pass
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data); f.flush()
            try:
                return subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=60).stdout.decode("utf-8", "ignore")
            except Exception:
                return ""
    txt = data.decode("utf-8", "ignore")
    if low.endswith((".htm", ".html")) or "html" in content_type or "<html" in txt[:500].lower():
        txt = re.sub(r"(?is)<(script|style).*?</\1>", " ", txt)
        txt = re.sub(r"(?i)<br\s*/?>|</(p|tr|div|li|h\d)>|</t[dh]>", "\n", txt)
        txt = re.sub(r"<[^>]+>", " ", txt)
        import html
        txt = html.unescape(txt)
    return txt


def _norm(t):
    t = t.replace(" ", " ").replace("−", "-").replace("–", "-").replace("—", "-").replace("m²", "m2").replace("㎡", "m2")
    return re.sub(r"[ \t]+", " ", t)


def _f(x):
    return float(x.replace(",", ".").replace(" ", ""))


def _ev(t, m, w=70):
    a, b = max(0, m.start() - w), min(len(t), m.end() + w)
    return re.sub(r"\s+", " ", t[a:b]).strip()


def _find(t, pat, flags=re.I | re.S):
    return re.search(pat, t, flags)


def parse_material(text):
    t = _norm(text)
    out = []

    def add(field, label_pl, label_en, value, unit, m, note=None):
        out.append(dict(field=field, label=L(label_pl, label_en), value=value, unit=unit, evidence=_ev(t, m), note=note, kind="value"))

    m = _find(t, r"(?:weight|mass|gramatura|masa powierzchniowa|Gewicht|Fl[äa]chengewicht)[^\d\n]{0,40}(\d{2,4}(?:[.,]\d)?)\s*(?:g\s*/\s*m2|gsm|g/m\^?2)")
    if m:
        add("gsm", "Gramatura", "Weight per area", _f(m.group(1)), "g/m²", m)
    m = _find(t, r"(?:thickness|grubo[śs][ćc]|Dicke|St[äa]rke|Gesamtdicke)[^\d\n]{0,40}(\d(?:[.,]\d+)?)\s*mm")
    if m:
        add("thickness_mm", "Grubość", "Thickness", _f(m.group(1)), "mm", m)
    for m in re.finditer(r"(-?\s*\d{1,3})\s*°\s*C?\s*(?:/|to|bis|do|\.{2,3}|…|-|and|÷)\s*\+?\s*(\d{1,3})\s*°\s*C", t, re.I):
        lo, hi = _f(m.group(1)), _f(m.group(2))
        if -100 <= lo < hi <= 1200:
            ctx = t[max(0, m.start() - 90):m.start()].lower()
            note = None if re.search(r"temperat|zakres|range|einsatz|service|operating", ctx) else L("kontekst temperatury niejednoznaczny — sprawdź w dokumencie, czy to zakres pracy ciągłej", "temperature context unclear - check that this is the continuous service range")
            add("tmin_c", "Temperatura min. (zakres)", "Min temperature (range)", lo, "°C", m, note)
            add("tmax_c", "Temperatura maks. (zakres)", "Max temperature (range)", hi, "°C", m, note)
            break
    m = _find(t, r"(?:tensile|breaking|zugfestigkeit|h[öo]chstzugkraft|wytrzyma[łl]o[śs][ćc] na (?:rozci[ąa]ganie|zerwanie))[^\d\n]{0,60}(\d{3,5})(?:\s*/\s*(\d{3,5}))?\s*N\s*/\s*(?:5\s*cm|50\s*mm)")
    if m:
        v = min(float(m.group(1)), float(m.group(2) or m.group(1)))
        add("tensile_n_50mm", "Wytrzymałość na rozciąganie (mniejsza z osnowy/wątku)", "Tensile strength (lower of warp/weft)", v, "N/50 mm", m)
    m = _find(t, r"(?:roll width|width|szeroko[śs][ćc]|Breite)[^\d\n]{0,30}(\d{2,4}(?:[.,]\d+)?)\s*(cm|mm)")
    if m:
        v = _f(m.group(1)) * (10 if m.group(2).lower() == "cm" else 1)
        add("roll_width_mm", "Szerokość materiału (wpisz w Konstrukcji → szerokość beli)", "Material width (enter in Cover design -> roll width)", v, "mm", m, L("pole projektu, nie rekordu bazy", "project field, not a catalogue field"))
    stds = []
    for m in re.finditer(r"\b(?:EN(?:\s?ISO)?|ISO|DIN|IEC|UL|NF|BS|ASTM)\s?[A-Z]?\s?\d{2,6}(?:-\d+)*\b", t):
        s = re.sub(r"\s+", " ", m.group(0))
        if s not in stds:
            stds.append(s)
    if stds:
        out.append(dict(field="standards", label=L("Normy wymienione w dokumencie (deklaracje — nie są interpretowane jako oceny)", "Standards mentioned in the document (claims - not interpreted as ratings)"),
                        value=stds[:20], unit="", evidence=", ".join(stds[:20]), note=L("sprawdź certyfikaty; aplikacja nie deklaruje zgodności", "check certificates; the app makes no compliance claims"), kind="info"))
    classes = {"mineral_oil": r"mineral oil|olej\w* mineral|hydraulic|olej\w* hydrauli|grease|smar", "acids": r"\bacids?\b|kwas", "alkalis": r"alkali|lye|zasad|ług", "solvents": r"solvent|rozpuszczal|ketone|aceton",
               "fuels": r"fuel|petrol|diesel|paliw|benzyn", "cutting_fluid": r"coolant|emulsion|emulsj|cutting fluid", "detergents": r"detergent|cleaner", "disinfectants": r"disinfect|dezynfek"}
    for k, pat in classes.items():
        m = _find(t, r"[^.\n]{0,60}(?:%s)[^.\n]{0,80}" % pat)
        if m:
            out.append(dict(field="chem." + k, label=L("Wzmianka o odporności chemicznej: " + k, "Chemical resistance mention: " + k), value=None, unit="", evidence=re.sub(r"\s+", " ", m.group(0)).strip(), kind="mention",
                            note=L("Oceń sam i wpisz ocenę 0–3 w sekcji „Oceny z dokumentu” — nie wyciągam ocen automatycznie.", "Judge yourself and enter a 0-3 rating in the 'Ratings from the document' section - ratings are not extracted automatically.")))
    comp = [k for k in ("polyester", "polyamide", "aramid", "kevlar", "nomex", "ptfe", "pvc", "polyurethane", "tpu", "silicone", "glass") if re.search(k, t, re.I)]
    if comp:
        out.append(dict(field="composition_hint", label=L("Wzmianki o składzie/powłoce", "Composition/coating mentions"), value=comp, unit="", evidence=", ".join(comp), kind="info", note=None))
    return out


def parse_robot(text):
    t = _norm(text)
    out = []

    def add(field, pl, en, v, unit, m):
        out.append(dict(field=field, label=L(pl, en), value=v, unit=unit, evidence=_ev(t, m), kind="value", note=None))
    m = _find(t, r"(?:max\.?\s*)?(?:reach|zasi[ęe]g|reichweite)[^\d\n]{0,40}(\d{3,4}(?:[.,]\d+)?)\s*mm")
    if m: add("reach_mm", "Zasięg", "Reach", _f(m.group(1)), "mm", m)
    m = _find(t, r"(?:payload|udźwig|traglast|rated load)[^\d\n]{0,40}(\d{1,3}(?:[.,]\d+)?)\s*kg")
    if m: add("payload_kg", "Udźwig", "Payload", _f(m.group(1)), "kg", m)
    m = _find(t, r"\b(\d)\s*[- ]?(?:axes|axis|osi|achsen)\b")
    if m: add("axes", "Liczba osi", "Axes", int(m.group(1)), "", m)
    m = _find(t, r"(?:robot )?(?:weight|masa|gewicht)[^\d\n]{0,30}(\d{1,4}(?:[.,]\d+)?)\s*kg")
    if m: add("mass_kg", "Masa robota", "Robot mass", _f(m.group(1)), "kg", m)
    m = _find(t, r"(?:repeatab|powtarzalno|wiederhol)[^\d\n]{0,40}[±+]\s*/?-?\s*(\d(?:[.,]\d+)?)\s*mm")
    if m: add("repeatability_mm", "Powtarzalność", "Repeatability", _f(m.group(1)), "mm", m)
    m = _find(t, r"(?:footprint|base (?:size|dimensions)|podstaw[ay])[^\d\n]{0,40}(\d{2,4})\s*[x×]\s*(\d{2,4})\s*mm")
    if m: out.append(dict(field="base_info", label=L("Wymiary podstawy (informacyjnie — wpisz w segmentach)", "Base dimensions (informational - enter in segments)"), value=[_f(m.group(1)), _f(m.group(2))], unit="mm", evidence=_ev(t, m), kind="info", note=None))
    return out


# ---------------------------------------------------------------- store + apply
def store_doc(name, data, source_url=None):
    sha = hashlib.sha256(data).hexdigest()
    d = db.DATA_DIR / "docs"; d.mkdir(exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:80]
    (d / f"{sha[:16]}_{safe}").write_bytes(data)
    return dict(id=sha[:16], sha256=sha, name=safe, source_url=source_url, bytes=len(data))


def analyse(target, name, data, content_type="", source_url=None):
    doc = store_doc(name, data, source_url)
    text = extract_text(name, data, content_type)
    doc["chars"] = len(text)
    if len(text.strip()) < 15:
        return dict(doc=doc, findings=[], warning=L("Z dokumentu nie wydobyto tekstu (skan/obraz?). Wymagany OCR lub ręczne wpisanie danych.", "No text could be extracted (scan/image?). OCR or manual entry is required."))
    return dict(doc=doc, findings=parse_material(text) if target == "material" else parse_robot(text), warning=None)


NUM_FIELDS = {"material": {"gsm": "range", "thickness_mm": "range", "tensile_n_50mm": "range", "tmin_c": "num", "tmax_c": "num"},
              "robot": {"reach_mm": "num", "payload_kg": "num", "axes": "num", "mass_kg": "num", "repeatability_mm": "num"}}
RATING_KEYS = {"material": ["chem." + k for k in ("mineral_oil", "cutting_fluid", "solvents", "detergents", "disinfectants", "acids", "alkalis", "fuels")] +
               ["abrasion", "tear", "cut", "puncture", "flex", "flame", "spark", "esd", "uv", "water", "cleanability", "dust", "antimicrobial"]}


def apply(target, rid, doc, accepted, ratings=None, product=None, as_new=False):
    kind = "materials" if target == "material" else "robots"
    base = db.catalog_get(kind, rid)
    if not base:
        raise ValueError("Unknown record.")
    if not (doc and doc.get("sha256")):
        raise ValueError("Source document metadata required.")
    patch, vf = {}, set(base.get("verified_fields") or [])
    for f, v in (accepted or {}).items():
        kindf = NUM_FIELDS[target].get(f)
        if not kindf or v in (None, ""):
            continue
        v = float(v)
        patch[f] = [v, v] if kindf == "range" else (int(v) if f == "axes" else v)
        vf.add(f)
    for k, v in (ratings or {}).items():
        if v in (None, "") or k not in RATING_KEYS.get(target, []):
            continue
        v = int(v)
        if not 0 <= v <= 3:
            raise ValueError("Rating must be 0-3.")
        if k.startswith("chem."):
            ch = dict(base.get("chem") or {}); ch.update(patch.get("chem", {})); ch[k[5:]] = v; patch["chem"] = ch
        else:
            patch[k] = v
        vf.add(k)
    if not vf - set(base.get("verified_fields") or []):
        raise ValueError("Nothing accepted - select at least one value or rating.")
    import datetime
    src = f"{doc['name']} (sha256:{doc['sha256'][:12]})" + (f" <{doc['source_url']}>" if doc.get("source_url") else "")
    patch.update(verified_fields=sorted(vf), source_document=src, source_date=datetime.date.today().isoformat(),
                 source=L("Dokument użytkownika: " + src + " — pola z listy verified_fields; pozostałe wartości typowe", "User document: " + src + " - fields in verified_fields; other values typical"))
    if doc.get("source_url"):
        patch["tds_url" if target == "material" else "doc_url"] = doc["source_url"]
    if base.get("confidence") != "verified":
        patch["confidence"] = "partial"
    if product:
        patch["product"] = product
    if as_new:
        if not product:
            raise ValueError("Product name required to create a new record.")
        slug = re.sub(r"[^a-z0-9]+", "-", product.lower()).strip("-")[:30]
        nid = f"{rid}__{slug}"
        rec = {**base, **patch, "id": nid, "_new": True, "name": L(product, product), "product": product}
        if target == "robot":
            rec.update(model=product)
        db.set_override(kind, nid, rec)
        return db.catalog_get(kind, nid)
    db.set_override(kind, rid, patch)
    return db.catalog_get(kind, rid)
