"""Project storage and content fingerprints. No model or network calls."""
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class Problem(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def token():
    return uuid.uuid4().hex[:12]


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise Problem("Invalid identifier: %r" % value)
    return value


def inside(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise Problem("Expected a nonempty project-relative path: %r" % name)
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts:
        raise Problem("Path must stay within project: " + name)
    root = Path(root).resolve()
    path = (root / rel).resolve()
    if root not in path.parents:
        raise Problem("Path escapes project: " + name)
    return path


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_json(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError) as exc:
        raise Problem("Cannot read JSON %s: %s" % (path, exc)) from exc


def save_json(path, value, backup=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        history = path.parent / "history"
        history.mkdir(exist_ok=True)
        shutil.copy2(path, history / (path.stem + "-" + token() + path.suffix))
    fd, temp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def project(root):
    p = read_json(Path(root) / "project.json")
    if not isinstance(p, dict) or p.get("version") != 1:
        raise Problem("Expected project schema version 1")
    for key in ("inputs", "sources", "assets", "units", "symbols", "domains"):
        if not isinstance(p.get(key), list):
            raise Problem("project.%s must be a list" % key)
    if p.get("mode") not in ("faithful", "study", "both") or not isinstance(p.get("title"), str) or not p["title"].strip():
        raise Problem("Project title or mode is invalid")
    if not all(isinstance(x, dict) for key in ("inputs", "sources", "assets", "symbols") for x in p[key]):
        raise Problem("Project records must be objects")
    for uid in p["units"]:
        identifier(uid)
    return p


def state(root):
    path = Path(root) / "state.json"
    return read_json(path) if path.exists() else {"version": 1, "reviews": {}, "builds": {}, "events": []}


def event(root, action, details):
    data = state(root)
    data["events"].append({"at": now(), "action": action, "details": details})
    save_json(Path(root) / "state.json", data)


@contextmanager
def locked(root):
    """One writer; a killed process leaves an explicit, inspectable lock."""
    path = Path(root) / ".econ-note.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise Problem("Project is locked. Check the PID in %s; remove it only after confirming no writer is running." % path) from exc
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump({"pid": os.getpid(), "at": now()}, stream)
        yield
    finally:
        path.unlink(missing_ok=True)


def units(root, p):
    result = []
    for uid in p["units"]:
        u = read_json(inside(root, "units/%s.json" % identifier(uid)))
        if not isinstance(u, dict) or u.get("id") != uid:
            raise Problem("Unit identity mismatch: " + uid)
        result.append(u)
    return result


def empty_unit(uid, title, source_ids):
    return {"id": identifier(uid), "title": title, "source_ids": source_ids, "coverage": [], "blocks": [], "issues": []}


def body_path(block, mode):
    bodies = block.get("body", {})
    if block.get("origin") == "explanation" and mode == "faithful":
        return None
    return bodies.get(mode) or (bodies.get("faithful") if mode == "study" else None)


def tracked_files(root, names):
    result = {}
    for name in sorted(set(names)):
        path = inside(root, name)
        result[name] = sha_file(path) if path.is_file() else "MISSING"
    return result


def unit_digest(root, p, unit):
    names = [v for b in unit.get("blocks", []) for v in b.get("body", {}).values()]
    if p.get("preamble"):
        names.append(p["preamble"])
    names += [a["path"] for a in p["assets"]]
    sources = [s for s in p["sources"] if s["id"] in unit.get("source_ids", [])]
    names += [s["image"] for s in sources if s.get("image")]
    return digest({"unit": unit, "sources": sources, "symbols": p["symbols"], "files": tracked_files(root, names)})


def fingerprint(root, p, all_units, template_dir=None):
    value = {"project": p, "units": [unit_digest(root, p, u) for u in all_units]}
    if template_dir is not None:
        value["templates"] = {f.name: sha_file(f) for f in sorted(Path(template_dir).glob("*.tex"))}
    return digest(value)


def check_box(box):
    import math
    return (isinstance(box, list) and len(box) == 4
            and all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) for n in box)
            and 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)
