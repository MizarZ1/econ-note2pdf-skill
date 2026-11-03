"""Structural validation and explicit host review attestations."""
import re
from pathlib import Path

from core import (Problem, body_path, check_box, fingerprint, identifier, inside,
                  now, project, save_json, sha_file, state, unit_digest, units)

KINDS = {"text", "equation", "derivation", "definition", "proposition", "proof", "example", "figure", "table", "summary", "heading"}
TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "latex"


def check_tex(text):
    """Reject file/tool operations in host-authored fragments; not a TeX sandbox."""
    if "^^" in text:
        raise Problem("TeX encoded characters are unsupported in course fragments")
    banned = r"input|include|includeonly|openin|openout|read|readline|write|immediate|newread|newwrite|csname|endcsname|catcode|def|edef|gdef|xdef|let|futurelet|scantokens|special|directlua|useLuaModule|pdfobj|pdfcatalog|pdfannot"
    if re.search(r"\\(?:" + banned + r")(?![A-Za-z@])", text):
        raise Problem("Fragment contains unsupported file access or executable TeX primitives")
    for name in re.findall(r"\\(?:usepackage|RequirePackage)(?:\[[^\]]*\])?\s*\{([^}]+)\}", text):
        if not re.fullmatch(r"[A-Za-z0-9_, -]+", name):
            raise Problem("Course packages must be ordinary installed package names")
    for path in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}", text):
        if not re.fullmatch(r"assets/[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]+)?", path):
            raise Problem("Image must use a literal registered assets/name path")


def validate(root):
    p, us = project(root), None
    out = {"errors": [], "gaps": [], "warnings": [], "unit_status": {}}
    errors, gaps, warnings = out["errors"], out["gaps"], out["warnings"]
    try:
        us = units(root, p)
    except Problem as exc:
        errors.append(str(exc))
        return out

    def fail(message, uid=None, gap=False):
        (gaps if gap else errors).append(("[%s] " % uid if uid else "") + message)
        if uid:
            out["unit_status"].setdefault(uid, {"errors": [], "gaps": []})["gaps" if gap else "errors"].append(message)

    def ids(records, label):
        found = {}
        for record in records:
            try:
                key = identifier(record.get("id"))
                if key in found:
                    fail("Duplicate %s ID: %s" % (label, key))
                found[key] = record
            except (Problem, AttributeError) as exc:
                fail("Invalid %s: %s" % (label, exc))
        return found

    inputs, sources = ids(p["inputs"], "input"), ids(p["sources"], "source")
    if not sources:
        fail("No sources", gap=True)
    if len(p["units"]) != len(set(p["units"])):
        fail("Duplicate unit IDs in project order")
    if not p["units"]:
        fail("No units", gap=True)
    if not all(d in {"macro", "micro", "econometrics", "math"} for d in p["domains"]):
        fail("Unknown domain")
    if not p.get("order_confirmed"):
        warnings.append("Input order is proposed; confirm against the material and set order_confirmed=true")
        fail("Source order has not been confirmed", gap=True)
    presentation = p.get("presentation", {})
    if not isinstance(presentation, dict):
        fail("presentation must be an object")
    else:
        if presentation.get("purpose", "revision") not in ("revision", "reference"):
            fail("presentation.purpose must be revision or reference")
        if presentation.get("source_style", "plain") not in ("plain", "accent", "box"):
            fail("presentation.source_style must be plain, accent or box")
    for symbol in p["symbols"]:
        try:
            check_tex(symbol.get("tex", ""))
        except Problem as exc:
            fail(str(exc))
        if not all(isinstance(symbol.get(k), str) and symbol[k].strip() for k in ("tex", "meaning", "scope")):
            fail("Each symbol needs tex, meaning and scope")
    if p.get("preamble"):
        try:
            path = inside(root, p["preamble"])
            if path.suffix != ".tex" or not path.is_file():
                fail("Course preamble must be an existing .tex file")
            else:
                check_tex(path.read_text(encoding="utf-8"))
            if path.is_file() and re.search(r"\\documentclass|\\(?:begin|end)\s*\{document\}", path.read_text(encoding="utf-8")):
                fail("Course preamble cannot contain document wrappers")
        except Problem as exc:
            fail(str(exc))
    for item in inputs.values():
        try:
            path = inside(root, item.get("path"))
            if not path.is_file() or sha_file(path) != item.get("sha256"):
                fail("Original missing or changed: " + str(item.get("path")))
        except Problem as exc:
            fail(str(exc))
    for s in sources.values():
        if s.get("input_id") not in inputs or not isinstance(s.get("page"), int) or s["page"] < 1:
            fail("Invalid input/page for " + s["id"])
        if not s.get("revision"):
            fail("Source not prepared: " + s["id"], gap=True)
        else:
            try:
                image = inside(root, s.get("image"))
                if not image.is_file() or sha_file(image) != s.get("image_sha256"):
                    fail("Prepared image missing or changed: " + s["id"])
            except Problem as exc:
                fail(str(exc))
    seen_assets = set()
    for asset in p["assets"]:
        try:
            path = inside(root, asset.get("path"))
            if asset.get("path") in seen_assets:
                fail("Duplicate asset path: " + asset["path"])
            seen_assets.add(asset.get("path"))
            if not path.is_file() or sha_file(path) != asset.get("sha256"):
                fail("Asset missing or modified: " + str(asset.get("path")))
            src = sources.get(asset.get("source_id"))
            if not src or src.get("revision") != asset.get("revision") or not check_box(asset.get("box")):
                fail("Asset has stale/invalid source: " + str(asset.get("path")))
        except Problem as exc:
            fail(str(exc))

    all_blocks = {}
    for u in us:
        uid = u["id"]
        out["unit_status"][uid] = {"errors": [], "gaps": []}
        for key in ("source_ids", "coverage", "blocks", "issues"):
            if not isinstance(u.get(key), list):
                fail(key + " must be a list", uid)
        if out["unit_status"][uid]["errors"]:
            continue
        for b in u["blocks"]:
            if not isinstance(b, dict):
                fail("Block must be an object", uid)
                continue
            try:
                bid = identifier(b.get("id"))
                if bid in all_blocks:
                    fail("Duplicate block ID: " + bid, uid)
                all_blocks[bid] = b
            except Problem as exc:
                fail(str(exc), uid)

    def ref_check(ref, uid, allowed):
        if not isinstance(ref, dict) or not check_box(ref.get("box")):
            fail("Invalid source reference box", uid)
            return
        sid = ref.get("source_id")
        s = sources.get(sid)
        if not s or sid not in allowed:
            fail("Reference source not assigned to unit: " + str(sid), uid)
        elif not s.get("revision"):
            fail("Reference source is not prepared: " + str(sid), uid, gap=True)
        elif ref.get("revision") != s["revision"]:
            fail("Stale source revision: " + str(sid), uid)

    covered_sources = set()
    covered_blocks = set()
    for u in us:
        uid = u["id"]
        if not all(isinstance(u.get(k), list) for k in ("source_ids", "coverage", "blocks", "issues")):
            continue
        if not isinstance(u.get("title"), str) or not u["title"].strip():
            fail("Unit needs a title", uid)
        allowed = u["source_ids"]
        if not allowed or any(not isinstance(s, str) or s not in sources for s in allowed):
            fail("Unit has unknown or empty source_ids", uid)
        blocks = [b for b in u["blocks"] if isinstance(b, dict)]
        bids = {b.get("id") for b in blocks if isinstance(b.get("id"), str)}
        if not u["coverage"]:
            fail("Coverage inventory is empty", uid, gap=True)
        if not blocks and not (u["coverage"] and all(isinstance(c, dict) and c.get("disposition") in ("excluded", "duplicate") for c in u["coverage"])):
            fail("No content blocks", uid, gap=True)
        issue_ids, corrected = set(), set()
        for issue in u["issues"]:
            if not isinstance(issue, dict):
                fail("Issue must be an object", uid)
                continue
            try:
                iid = identifier(issue.get("id"))
                if iid in issue_ids:
                    fail("Duplicate issue: " + iid, uid)
                issue_ids.add(iid)
            except Problem as exc:
                fail(str(exc), uid)
            links = issue.get("block_ids")
            if not isinstance(links, list) or any(not isinstance(b, str) or b not in bids for b in links):
                fail("Issue references unknown blocks", uid)
                links = []
            if issue.get("severity") not in ("note", "critical") or issue.get("status") not in ("open", "resolved"):
                fail("Invalid issue severity/status", uid)
            if not all(isinstance(issue.get(k), str) and issue[k].strip() for k in ("summary", "detail")):
                fail("Issue needs summary and detail", uid)
            if issue.get("severity") == "critical" and issue.get("status") == "open":
                if not links:
                    fail("Open critical issue needs an affected block", uid)
                fail("Critical issue: " + str(issue.get("summary")), uid, gap=True)
            corrected.update(links)
        for b in blocks:
            bid = str(b.get("id"))
            origin = b.get("origin")
            if b.get("kind") not in KINDS or origin not in ("source", "explanation", "correction"):
                fail("Invalid block kind/origin: " + bid, uid)
            refs = b.get("refs")
            if not isinstance(refs, list):
                fail("Block refs must be a list: " + bid, uid)
                refs = []
            if origin != "explanation" and not refs:
                fail("Source/correction block needs references: " + bid, uid)
            for ref in refs:
                ref_check(ref, uid, allowed)
            bodies = b.get("body")
            if not isinstance(bodies, dict) or any(k not in ("faithful", "study") for k in bodies):
                fail("Invalid body map: " + bid, uid)
                continue
            if origin == "explanation" and not bodies.get("study"):
                fail("Explanation needs study body: " + bid, uid)
            if origin == "correction" and (not all(bodies.get(m) for m in ("faithful", "study")) or bid not in corrected):
                fail("Correction needs both versions and an academic issue: " + bid, uid)
            for mode in (("faithful", "study") if p["mode"] == "both" else (p["mode"],)):
                if origin == "explanation" and mode == "faithful":
                    continue
                if not body_path(b, mode):
                    fail("Missing %s body for %s" % (mode, bid), uid, gap=True)
            for path_name in bodies.values():
                try:
                    path = inside(root, path_name)
                    if path.suffix != ".tex" or not path.is_file():
                        fail("Missing .tex fragment: " + str(path_name), uid)
                        continue
                    text = path.read_text(encoding="utf-8")
                    check_tex(text)
                    if not text.strip() or not re.sub(r"(?m)(?<!\\)%.*$", "", text).strip():
                        fail("Empty body: " + path_name, uid, gap=True)
                    if re.search(r"\\documentclass|\\(?:begin|end)\s*\{document\}", text):
                        fail("Fragment must contain body only: " + path_name, uid)
                except (Problem, UnicodeError) as exc:
                    fail(str(exc), uid)
        cids = set()
        for c in u["coverage"]:
            if not isinstance(c, dict):
                fail("Coverage entry must be an object", uid)
                continue
            try:
                cid = identifier(c.get("id"))
                if cid in cids:
                    fail("Duplicate coverage ID: " + cid, uid)
                cids.add(cid)
            except Problem as exc:
                fail(str(exc), uid)
            ref_check(c, uid, allowed)
            covered_sources.add(c.get("source_id"))
            disposition = c.get("disposition")
            links = c.get("block_ids")
            if not isinstance(links, list) or any(not isinstance(b, str) or b not in all_blocks for b in links):
                fail("Coverage references unknown blocks", uid)
                links = []
            if disposition not in ("included", "duplicate", "excluded", "unreadable") or c.get("kind") not in KINDS:
                fail("Invalid coverage kind/disposition", uid)
            if disposition in ("included", "duplicate") and not links:
                fail("Included/duplicate region needs kept blocks", uid)
            if disposition != "included" and (not isinstance(c.get("reason"), str) or not c["reason"].strip()):
                fail("Excluded/duplicate/unreadable region needs reason", uid)
            if disposition == "included":
                for bid in links:
                    b = all_blocks[bid]
                    if bid not in bids or b.get("origin") == "explanation" or not any(isinstance(r, dict) and r.get("source_id") == c.get("source_id") for r in b.get("refs", [])):
                        fail("Included region does not match source block: " + bid, uid)
                covered_blocks.update(links)
            if disposition == "unreadable":
                fail("Unreadable region: " + str(c.get("reason")), uid, gap=True)
                if not links or not any(b in corrected for b in links):
                    fail("Unreadable region needs placeholder block and academic issue", uid)
                covered_blocks.update(links)
    for sid in sources:
        if sid not in covered_sources:
            fail("Source has no coverage inventory: " + sid, gap=True)
    for bid, b in all_blocks.items():
        if b.get("origin") != "explanation" and bid not in covered_blocks:
            fail("Source block has no included/unreadable coverage: " + bid)
    return out


def status(root):
    p, us, s = project(root), units(root, project(root)), state(root)
    report = validate(root)
    result = {"validation": report, "units": [], "builds": {}}
    for u in us:
        try:
            if report["errors"]:
                raise Problem("Cannot certify structurally invalid content")
            current = unit_digest(root, p, u)
            reviewed = s["reviews"].get(u["id"], {}).get("digest") == current
        except (Problem, TypeError, KeyError):
            reviewed = False
        result["units"].append({"id": u["id"], "content_review_current": reviewed,
                                **report["unit_status"].get(u["id"], {})})
    try:
        if report["errors"]:
            raise Problem("Invalid input")
        current = fingerprint(root, p, us, TEMPLATES)
    except (Problem, TypeError, KeyError):
        current = None
    for mode, b in s["builds"].items():
        from build import rendering_current, source_digest
        pdf = Path(root) / "build" / mode / "main.pdf"
        pdf_current = bool(b.get("compiled") and pdf.is_file() and sha_file(pdf) == b.get("pdf_sha256"))
        stale = b.get("fingerprint") != current or b.get("source_digest") != source_digest(pdf.parent)
        lr = b.get("layout_review") or {}
        from core import digest
        layout_current = (not stale and pdf_current and rendering_current(root, b)
                          and lr.get("pdf_sha256") == b.get("pdf_sha256") and lr.get("render_digest") == digest(b["render"]))
        result["builds"][mode] = {**b, "stale": stale, "pdf_current": pdf_current, "layout_review_current": bool(layout_current)}
    return result


def review_content(args):
    root = Path(args.project)
    p, report = project(root), validate(root)
    if report["errors"]:
        raise Problem("Fix structural errors before recording a review: " + "; ".join(report["errors"]))
    selected = [u for u in units(root, p) if u["id"] == args.unit]
    if len(selected) != 1:
        raise Problem("Unknown review unit")
    u = selected[0]
    if not u["coverage"] or any(not next(s for s in p["sources"] if s["id"] == sid).get("revision") for sid in u["source_ids"]):
        raise Problem("Prepare sources and complete the inventory before review")
    if any("Missing " in g or "Empty body" in g or "No content" in g for g in report["unit_status"][u["id"]]["gaps"]):
        raise Problem("Complete the unit content before review")
    s = state(root)
    attestation = {"digest": unit_digest(root, p, u), "at": now(), "note": args.note, "by": "host-agent"}
    s["reviews"][u["id"]] = attestation
    save_json(root / "state.json", s)
    return {"unit": u["id"], "review": attestation}
