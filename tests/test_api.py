import os, tempfile
os.environ["RCD_DATA_DIR"] = tempfile.mkdtemp()
import ezdxf, io
from fastapi.testclient import TestClient
from rcd.api import app

c = TestClient(app)


def mk():
    return c.post("/api/projects", json={"example": True}).json()["id"]


def test_exports_are_valid_files():
    pid = mk()
    assert c.post(f"/api/projects/{pid}/run").json()["stage"] == "complete"
    pdf = c.get(f"/api/projects/{pid}/export/pattern.pdf"); assert pdf.content[:4] == b"%PDF"
    assert c.get(f"/api/projects/{pid}/export/docs.pdf").content[:4] == b"%PDF"
    d = c.get(f"/api/projects/{pid}/export/pattern.dxf")
    doc = ezdxf.read(io.StringIO(d.content.decode()))
    layers = {e.dxf.layer for e in doc.modelspace()}
    assert {"CUT", "SEW", "CONTROL"} <= layers
    assert "<svg" in c.get(f"/api/projects/{pid}/export/marker.svg").text
    assert c.get(f"/api/projects/{pid}/export/bom.csv").status_code == 200


def test_approval_blocked_with_critical_error_and_reset_on_edit():
    pid = mk()
    assert c.post(f"/api/projects/{pid}/approve").status_code == 200
    p = c.get(f"/api/projects/{pid}").json()
    p["requirements"].update(zipper=False, velcro=False, snaps=False)
    c.put(f"/api/projects/{pid}", json=p)
    assert c.get(f"/api/projects/{pid}").json()["status"] == "draft"
    assert c.post(f"/api/projects/{pid}/approve").status_code == 409


def test_verified_status_requires_source():
    assert c.put("/api/db/materials/pvc_pes", json={"confidence": "verified"}).status_code == 422
    r = c.put("/api/db/materials/pvc_pes", json={"confidence": "verified", "tds_url": "https://example.com/tds.pdf"})
    assert r.status_code == 200 and r.json()["confidence"] == "verified"


def test_assistant_returns_suggestions_only():
    r = c.post("/api/assist/environment", json={"text": "ciągły kontakt z emulsją chłodzącą, iskry spawalnicze"}).json()
    assert {x["key"] for x in r} >= {"emulsion", "sparks"} and all("note" in x for x in r)


def test_stl_upload_bbox():
    pid = mk()
    stl = b"solid x\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 100 0 0\nvertex 0 50 200\nendloop\nendfacet\nendsolid x\n"
    r = c.post(f"/api/projects/{pid}/upload?kind=model", files={"file": ("m.stl", stl)}).json()
    assert r["bbox"]["size"] == [100.0, 50.0, 200.0]
