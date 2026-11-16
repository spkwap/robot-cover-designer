import os, tempfile, threading, http.server, socketserver, io
os.environ["RCD_DATA_DIR"] = tempfile.mkdtemp()
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from rcd.api import app
from rcd import ingest, pipeline, example
import copy

c = TestClient(app)
TDS = ["TECHNICAL DATA SHEET - Example TPU coated fabric X1", "Total weight: 480 g/m2 (EN ISO 2286-2)", "Thickness: 0.45 mm",
       "Tensile strength warp/weft: 3200/2800 N/5 cm", "Operating temperature: -30 °C to +80 °C", "Width: 150 cm", "Resistant to mineral oil and hydraulic fluids.",
       "Flame retardant: DIN 4102-B1"]


def pdf_bytes():
    b = io.BytesIO(); cv = canvas.Canvas(b); y = 800
    for l in TDS:
        cv.drawString(50, y, l); y -= 20
    cv.save(); return b.getvalue()


def test_pdf_extraction_proposes_values_with_evidence():
    r = c.post("/api/ingest/file?target=material", files={"file": ("x1.pdf", pdf_bytes(), "application/pdf")}).json()
    f = {x["field"]: x for x in r["findings"]}
    assert f["gsm"]["value"] == 480 and f["thickness_mm"]["value"] == 0.45
    assert f["tensile_n_50mm"]["value"] == 2800            # lower of warp/weft
    assert (f["tmin_c"]["value"], f["tmax_c"]["value"]) == (-30, 80)
    assert f["roll_width_mm"]["value"] == 1500
    assert "480" in f["gsm"]["evidence"]
    assert f["chem.mineral_oil"]["value"] is None          # ratings are never auto-extracted
    assert any("DIN 4102" in s for s in f["standards"]["value"])


def test_apply_marks_only_accepted_fields_verified_and_creates_new_record():
    r = c.post("/api/ingest/file?target=material", files={"file": ("x1.pdf", pdf_bytes(), "application/pdf")}).json()
    out = c.post("/api/ingest/apply", json=dict(target="material", id="pu_pes", doc=r["doc"], accepted={"gsm": 480, "tmax_c": 80}, ratings={"chem.mineral_oil": 3},
                                                 product="Example X1 TPU", as_new=True)).json()
    assert set(out["verified_fields"]) == {"gsm", "tmax_c", "chem.mineral_oil"}
    assert out["gsm"] == [480, 480] and out["id"].startswith("pu_pes__") and out["confidence"] == "partial"
    base = c.get("/api/db/materials").json()
    assert next(m for m in base if m["id"] == "pu_pes").get("verified_fields") is None       # family record untouched


def test_verified_field_turns_check_green_but_others_stay_yellow():
    from rcd.engines import materials as M, environment as E
    from rcd import db
    rec = next(m for m in db.catalog("materials") if "__" in m["id"])
    env = {"tmin_c": 5, "tmax_c": 40, "factors": {"oil_industrial": {"state": "present", "level": 2}}}
    ev = M.evaluate(rec, E.derive_requirements(env, db.default_requirements()))
    st = {x["req"]: x["status"] for x in ev["checks"]}
    assert st["chem:mineral_oil"] == "ok" and st["temp:max"] == "ok" and st["temp:min"] == "ok_unverified"
    assert not ev["verified"]


def test_nothing_accepted_is_rejected():
    r = c.post("/api/ingest/file?target=material", files={"file": ("x1.pdf", pdf_bytes(), "application/pdf")}).json()
    assert c.post("/api/ingest/apply", json=dict(target="material", id="pu_pes", doc=r["doc"], accepted={})).status_code == 422


def test_url_fetch_and_ssrf_guard():
    assert c.post("/api/ingest/url", json={"url": "http://127.0.0.1:1/x.pdf"}).status_code == 422    # blocked: private
    assert c.post("/api/ingest/url", json={"url": "file:///etc/passwd"}).status_code == 422
    os.environ["RCD_ALLOW_PRIVATE_URLS"] = "1"
    d = tempfile.mkdtemp(); open(os.path.join(d, "t.html"), "w").write("<html><body><p>Weight: 300 g/m2</p><p>Thickness 0.30 mm</p></body></html>")
    h = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=d, **k)
    srv = socketserver.TCPServer(("127.0.0.1", 0), h); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = c.post("/api/ingest/url", json={"url": f"http://127.0.0.1:{port}/t.html"}).json()
        assert {x["field"]: x["value"] for x in r["findings"]}["gsm"] == 300
    finally:
        srv.shutdown(); os.environ.pop("RCD_ALLOW_PRIVATE_URLS")


def test_robot_datasheet_extraction():
    t = "Reach: 850 mm\nPayload: 5 kg\n6 axes\nRepeatability ±0.03 mm\nWeight: 20.6 kg"
    f = {x["field"]: x["value"] for x in ingest.parse_robot(t)}
    assert f == {"reach_mm": 850, "payload_kg": 5, "axes": 6, "mass_kg": 20.6, "repeatability_mm": 0.03}


def test_pipeline_uses_verified_gsm_and_thickness():
    from rcd import db
    rec = next(m for m in db.catalog("materials") if "__" in m["id"])
    p = copy.deepcopy(example.EXAMPLE); p["id"] = "i"; p["requirements"]["material_override"] = rec["id"]
    r = pipeline.run(p)
    assert r["material"]["recommended"]["effective"]["gsm_confirmed"] and r["material"]["recommended"]["effective"]["gsm"] == 480
