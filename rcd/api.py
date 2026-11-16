"""FastAPI application: REST API + static frontend."""
import copy
import json
import re
import struct
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import db, pipeline, ingest
from .example import EXAMPLE
from .engines import environment as E, documentation as D
from .engines import geometry as G
from .export import svg as SVG, dxf as DXF, pdfs

app = FastAPI(title="Industrial Robot Protective Cover Designer", version="1.0")
FRONT = Path(__file__).resolve().parent.parent / "frontend"
STAGES = ["robot", "environment", "material", "design", "pattern", "sewing", "bom", "docs"]


def _proj(pid):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "project not found")
    return p


def _run(p):
    res = pipeline.run(p)
    if "construction" in res:
        res["construction"].pop("segs", None)
    p["results"] = {k: res.get(k) for k in ("stage",)}
    stage = res.get("stage")
    prog = dict(robot=not res["geometry"]["errors"], environment=stage not in ("geometry", "environment"),
                material="material" in res, design="construction" in res and bool(res["construction"].get("sections")),
                pattern="pattern" in res, sewing="sewing" in res, bom="bom" in res, docs=stage == "complete")
    p["progress"] = prog
    if "validation" in res:
        p["validation_summary"] = res["validation"]["summary"]
        if p.get("status") == "approved" and not res["validation"]["summary"]["can_approve"]:
            p["status"] = "draft"
    db.save_project(p)
    return res


@app.get("/api/health")
def health():
    return dict(ok=True)


@app.get("/api/meta")
def meta():
    return dict(factors=E.FACTORS, level_labels=E.LEVEL_LABELS, chem=E.CHEM_LABEL, props=E.PROP_LABEL, ratings=E.RATING_LABEL,
                defaults=db.default_requirements(), shapes=list(G.SHAPES))


@app.get("/api/robots")
def robots(q: str = ""):
    q = q.lower().strip()
    return [r for r in db.catalog("robots") if not q or q in f"{r['manufacturer']} {r['model']}".lower()]


@app.get("/api/db/{kind}")
def db_list(kind: str):
    if kind not in db.KINDS:
        raise HTTPException(404)
    return db.catalog(kind)


@app.put("/api/db/{kind}/{rid}")
def db_put(kind: str, rid: str, patch: dict):
    if kind not in db.KINDS:
        raise HTTPException(404)
    if patch.get("confidence") == "verified" and not (patch.get("tds_url") or patch.get("source_document")):
        raise HTTPException(422, "Status 'verified' requires tds_url or source_document (no invented data).")
    patch = {k: v for k, v in patch.items() if k != "id"}
    db.set_override(kind, rid, patch)
    return db.catalog_get(kind, rid)


@app.get("/api/projects")
def projects():
    return db.list_projects()


@app.post("/api/projects")
def create(body: dict):
    tpl = copy.deepcopy(EXAMPLE) if body.get("example") else None
    p = db.new_project(body.get("name") or (tpl or {}).get("name") or "New project", tpl)
    return p


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    return _proj(pid)


@app.put("/api/projects/{pid}")
def put_project(pid: str, body: dict):
    p = _proj(pid)
    for k in ("name", "robot", "environment", "requirements"):
        if k in body:
            p[k] = body[k]
    if p.get("status") == "approved":
        p["status"] = "draft"          # any change invalidates the approval
    db.save_project(p)
    return p


@app.delete("/api/projects/{pid}")
def delete(pid: str):
    db.delete_project(pid)
    return dict(ok=True)


@app.post("/api/projects/{pid}/run")
def run(pid: str):
    p = _proj(pid)
    return JSONResponse(_run(p))


@app.post("/api/projects/{pid}/approve")
def approve(pid: str):
    p = _proj(pid)
    res = _run(p)
    if res.get("stage") != "complete":
        raise HTTPException(409, "Project is incomplete - resolve the missing data first.")
    reds = [c for c in res["validation"]["checks"] if c["status"] == "red"]
    if reds:
        raise HTTPException(409, dict(message="Critical errors must be resolved before approval.", checks=[c["id"] for c in reds]))
    p["status"] = "approved"
    db.save_project(p)
    return dict(ok=True, status="approved")


@app.post("/api/ingest/url")
def ingest_url(body: dict):
    try:
        data, ct, final, name = ingest.fetch_url(body.get("url", ""))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return ingest.analyse(body.get("target", "material"), name, data, ct, final)


@app.post("/api/ingest/file")
async def ingest_file(target: str = Query("material"), file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > ingest.MAX_BYTES:
        raise HTTPException(413, "File too large")
    return ingest.analyse(target, file.filename or "document", data, file.content_type or "")


@app.post("/api/ingest/apply")
def ingest_apply(body: dict):
    try:
        return ingest.apply(body.get("target", "material"), body.get("id"), body.get("doc"), body.get("accepted"), body.get("ratings"), body.get("product"), bool(body.get("as_new")))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/assist/environment")
def assist(body: dict):
    return E.assist_text(body.get("text", ""))


def _bbox_from_model(name, data):
    ext = name.lower().rsplit(".", 1)[-1]
    pts = []
    if ext == "stl":
        if data[:5].lower() == b"solid" and b"facet" in data[:400]:
            for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data):
                pts.append(tuple(float(x) for x in m.groups()))
        else:
            n = struct.unpack("<I", data[80:84])[0]
            for i in range(n):
                o = 84 + i * 50 + 12
                for k in range(3):
                    pts.append(struct.unpack("<fff", data[o + 12 * k:o + 12 * k + 12]))
    elif ext == "obj":
        for line in data.decode("utf-8", "ignore").splitlines():
            if line.startswith("v "):
                pts.append(tuple(float(x) for x in line.split()[1:4]))
    elif ext == "dxf":
        import ezdxf
        import io
        doc = ezdxf.read(io.StringIO(data.decode("utf-8", "ignore")))
        from ezdxf import bbox as zb
        bb = zb.extents(doc.modelspace())
        if bb.has_data:
            return dict(min=list(bb.extmin), max=list(bb.extmax), size=list(bb.size), format="dxf")
    else:
        return None
    if not pts:
        return None
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    return dict(min=mn, max=mx, size=[b - a for a, b in zip(mn, mx)], format=ext, points=len(pts))


@app.post("/api/projects/{pid}/upload")
async def upload(pid: str, kind: str = Query("photo"), file: UploadFile = File(...)):
    p = _proj(pid)
    data = await file.read()
    if len(data) > 60 * 1024 * 1024:
        raise HTTPException(413, "File too large")
    d = db.DATA_DIR / "uploads" / pid
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "file")
    (d / safe).write_bytes(data)
    rec = dict(name=safe, kind=kind, size=len(data))
    if kind == "model":
        try:
            rec["bbox"] = _bbox_from_model(safe, data)
        except Exception as e:
            rec["error"] = str(e)
        if rec.get("bbox") is None and "error" not in rec:
            rec["error"] = "Unsupported/empty model. STL/OBJ/DXF bounding box is supported; STEP needs a CAD kernel (not included)."
    p["files"] = [f for f in p.get("files", []) if f["name"] != safe] + [rec]
    db.save_project(p)
    return rec


@app.get("/api/projects/{pid}/files/{name}")
def get_file(pid: str, name: str):
    f = db.DATA_DIR / "uploads" / pid / re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)


@app.get("/api/projects/{pid}/export/{what}")
def export(pid: str, what: str, lang: str = "pl", sheet: str = "A4"):
    p = _proj(pid)
    res = pipeline.run(p)
    if res.get("stage") not in ("complete",):
        raise HTTPException(409, "Project incomplete - nothing to export yet.")
    nm = re.sub(r"[^A-Za-z0-9_-]+", "_", p["name"])[:40] or "project"
    if what == "pattern.pdf":
        return Response(pdfs.pattern_pdf(res, p, lang, sheet), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nm}_pattern_{sheet}.pdf"'})
    if what == "pattern.dxf":
        return Response(DXF.marker_dxf(res), media_type="application/dxf", headers={"Content-Disposition": f'attachment; filename="{nm}_pattern.dxf"'})
    if what == "marker.svg":
        return Response(SVG.marker_svg(res, lang), media_type="image/svg+xml", headers={"Content-Disposition": f'attachment; filename="{nm}_marker.svg"'})
    if what == "docs.pdf":
        return Response(pdfs.docs_pdf(D.build(p, res, lang)), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nm}_documentation.pdf"'})
    if what == "bom.csv":
        return Response(pdfs.bom_csv(res["bom"], lang), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{nm}_bom.csv"'})
    if what == "marker.inline.svg":
        return Response(SVG.marker_svg(res, lang), media_type="image/svg+xml")
    m = re.match(r"piece-(\d+)\.svg", what)
    if m:
        pc = next((x for x in res["pattern"]["pieces"] if x["no"] == int(m.group(1))), None)
        if not pc:
            raise HTTPException(404)
        return Response(SVG.piece_svg(pc, lang), media_type="image/svg+xml")
    raise HTTPException(404)


@app.get("/api/projects/{pid}/docs")
def docs(pid: str, lang: str = "pl"):
    p = _proj(pid)
    res = pipeline.run(p)
    if res.get("stage") != "complete":
        raise HTTPException(409, "Project incomplete")
    return D.build(p, res, lang)


app.mount("/", StaticFiles(directory=str(FRONT), html=True), name="front")
