"""Persistence: projects in SQLite (repository layer isolated so it can be swapped for PostgreSQL),
catalog = built-in records + user overrides (overrides.json)."""
import copy
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

from .data import catalog as C

DATA_DIR = Path(os.environ.get("RCD_DATA_DIR", Path(__file__).resolve().parent.parent / "var"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
KINDS = {"materials": C.MATERIALS, "threads": C.THREADS, "machines": C.MACHINES,
         "accessories": C.ACCESSORIES, "robots": C.ROBOTS}


def _overrides():
    p = DATA_DIR / "overrides.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def catalog(kind):
    ov = _overrides().get(kind, {})
    out = []
    for rec in KINDS[kind]:
        r = copy.deepcopy(rec)
        if r["id"] in ov:
            r.update(ov[r["id"]])
        out.append(r)
    for rid, rec in ov.items():           # user-added records
        if not any(r["id"] == rid for r in out) and rec.get("_new"):
            out.append(rec)
    return out


def catalog_get(kind, rid):
    for r in catalog(kind):
        if r["id"] == rid:
            return r
    return None


def set_override(kind, rid, patch):
    ov = _overrides()
    ov.setdefault(kind, {}).setdefault(rid, {}).update(patch)
    (DATA_DIR / "overrides.json").write_text(json.dumps(ov, ensure_ascii=False, indent=1), encoding="utf-8")


def _conn():
    c = sqlite3.connect(DATA_DIR / "projects.sqlite3")
    c.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT, status TEXT, created REAL, updated REAL, data TEXT)")
    return c


def list_projects():
    with _conn() as c:
        rows = c.execute("SELECT id,name,status,created,updated,data FROM projects ORDER BY updated DESC").fetchall()
    out = []
    for r in rows:
        d = json.loads(r[5])
        out.append(dict(id=r[0], name=r[1], status=r[2], created=r[3], updated=r[4],
                        robot=f"{d.get('robot', {}).get('manufacturer', '')} {d.get('robot', {}).get('model', '')}".strip(),
                        progress=d.get("progress", {})))
    return out


def get_project(pid):
    with _conn() as c:
        r = c.execute("SELECT data FROM projects WHERE id=?", (pid,)).fetchone()
    return json.loads(r[0]) if r else None


def save_project(p):
    now = time.time()
    p["updated"] = now
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?)",
                  (p["id"], p.get("name", ""), p.get("status", "draft"), p.get("created", now), now,
                   json.dumps(p, ensure_ascii=False)))
    return p


def new_project(name, template=None):
    pid = uuid.uuid4().hex[:10]
    p = copy.deepcopy(template) if template else {}
    p.update(id=pid, name=name, status="draft", created=time.time())
    p.setdefault("robot", {"manufacturer": "", "model": "", "segments": []})
    p.setdefault("environment", {"factors": {}})
    p.setdefault("requirements", default_requirements())
    p.setdefault("results", {})
    p.setdefault("files", [])
    return save_project(p)


def delete_project(pid):
    with _conn() as c:
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


def default_requirements():
    return dict(scope="full", removable=True, modular=True, zipper=True, velcro=True, snaps=False, elastic=True,
                openings=True, service_access=True, easy_clean=True, removal_per_month=4, lifetime_years=3,
                max_mass_kg=None, color="", marking="", roll_width_mm=1500, allow_rotate_90=False, layers=1,
                pleat_height_mm=20, material_override=None, confirmed={})
