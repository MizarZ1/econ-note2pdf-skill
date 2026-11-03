"""Deterministic intake and image preparation with immutable revisions."""
import importlib.util
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from core import (Problem, check_box, digest, empty_unit, event, identifier,
                  inside, project, save_json, sha_file, token)

FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf", ".heic", ".heif"}


def doctor():
    packages = {name: importlib.util.find_spec(name) is not None for name in ("PIL", "pypdf", "pillow_heif")}
    binaries = {name: shutil.which(name) for name in ("pdftoppm", "pdfinfo", "xelatex", "latexmk", "sips")}
    return {"packages": packages, "tools": binaries,
            "capabilities": {"images": packages["PIL"], "pdf_intake": packages["pypdf"] and bool(binaries["pdftoppm"]),
                             "pdf_compile": bool(binaries["xelatex"] and binaries["latexmk"]), "pdf_preview": bool(binaries["pdftoppm"])},
            "python_minimum": "3.9", "model": "host agent; no API calls",
            "required_missing": [name for name in ("PIL", "pypdf") if not packages[name]]}


def open_image(path, frame=1):
    from PIL import Image, ImageOps
    if importlib.util.find_spec("pillow_heif"):
        import pillow_heif
        pillow_heif.register_heif_opener()
    try:
        with Image.open(path) as im:
            im.seek(frame - 1)
            result = ImageOps.exif_transpose(im).convert("RGB")
            result.load()
            return result
    except (OSError, ValueError, EOFError, Image.DecompressionBombError) as exc:
        if Path(path).suffix.lower() in (".heic", ".heif") and shutil.which("sips"):
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "converted.png"
                run = subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(dest)], capture_output=True, timeout=60)
                if run.returncode == 0 and dest.is_file():
                    return open_image(dest)
        raise Problem("Cannot decode image %s: %s" % (path, exc)) from exc


def page_count(path):
    try:
        return _page_count(path)
    except Problem:
        raise
    except Exception as exc:
        raise Problem("Cannot inspect input %s: %s" % (path.name, exc)) from exc


def _page_count(path):
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise Problem("Password-protected PDF is unsupported: " + path.name)
        return len(reader.pages)
    if path.suffix.lower() in (".heic", ".heif"):
        open_image(path)
        return 1
    from PIL import Image
    with Image.open(path) as im:
        count = getattr(im, "n_frames", 1)
        if count > 1 and path.suffix.lower() not in (".tif", ".tiff"):
            raise Problem("Animated images are unsupported; export still frames: " + path.name)
        return count


def initialize(args):
    root = Path(args.project).expanduser().resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise Problem("Initialization requires a new or empty directory")
    inputs, proposed = [], False
    for name in args.inputs:
        path = Path(name).expanduser().resolve()
        if path.is_dir():
            proposed = True
            natural = lambda p: [int(v) if v.isdigit() else v.lower() for v in re.split(r"(\d+)", p.name)]
            inputs.extend(sorted((p for p in path.iterdir() if p.is_file() and p.suffix.lower() in FORMATS), key=natural))
        elif path.is_file() and path.suffix.lower() in FORMATS:
            inputs.append(path)
        else:
            raise Problem("Unsupported or missing input: " + str(path))
    if not inputs:
        raise Problem("No supported input files")
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".econ-init-", dir=root.parent))
    try:
        for name in ("originals", "prepared", "assets", "units", "content", "history", "logs", "build", "previews", "output"):
            (stage / name).mkdir()
        p = {"version": 1, "title": args.title, "mode": args.mode, "domains": args.domains,
             "presentation": {"purpose": args.purpose, "source_style": args.source_style},
             "inputs": [], "sources": [], "assets": [], "units": [], "symbols": [], "order_confirmed": not proposed}
        for i, src in enumerate(inputs, 1):
            iid = "i%04d" % i
            rel = "originals/%s%s" % (iid, src.suffix.lower())
            shutil.copy2(src, stage / rel)
            p["inputs"].append({"id": iid, "name": src.name, "path": rel, "sha256": sha_file(stage / rel)})
            for page in range(1, page_count(stage / rel) + 1):
                sid = "s%04d" % (len(p["sources"]) + 1)
                uid = "u%03d" % (len(p["units"]) + 1)
                p["sources"].append({"id": sid, "input_id": iid, "page": page, "revision": None,
                                     "image": None, "preview": None, "size": [], "tiles": [], "transform": {}})
                p["units"].append(uid)
                save_json(stage / "units" / (uid + ".json"), empty_unit(uid, src.stem + " · " + str(page), [sid]))
        save_json(stage / "project.json", p)
        event(stage, "init", {"sources": len(p["sources"])})
        if root.exists():
            root.rmdir()  # verified empty; do not remove any user file
        stage.rename(root)
        return {"project": str(root), "sources": p["sources"], "order_confirmed": p["order_confirmed"]}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def source_record(p, sid):
    found = [s for s in p["sources"] if s["id"] == sid]
    if len(found) != 1:
        raise Problem("Unknown or duplicate source: " + sid)
    return found[0]


def load_source(root, p, source, dpi, temp):
    inp = next(i for i in p["inputs"] if i["id"] == source["input_id"])
    path = inside(root, inp["path"])
    if sha_file(path) != inp["sha256"]:
        raise Problem("Original file has changed: " + inp["path"])
    if path.suffix.lower() != ".pdf":
        return open_image(path, source["page"])
    if not shutil.which("pdftoppm"):
        raise Problem("pdftoppm is required to render PDF sources")
    out = Path(temp) / "pdf-page"
    run = subprocess.run(["pdftoppm", "-f", str(source["page"]), "-l", str(source["page"]),
                          "-r", str(dpi), "-singlefile", "-png", str(path), str(out)], capture_output=True, timeout=180)
    if run.returncode:
        raise Problem("PDF rendering failed: " + run.stderr.decode(errors="replace")[-2000:])
    return open_image(out.with_suffix(".png"))


def positions(size, tile, overlap):
    if size <= tile:
        return [0]
    values = list(range(0, size - tile + 1, max(1, round(tile * (1 - overlap)))))
    if values[-1] != size - tile:
        values.append(size - tile)
    return values


def perspective(im, quad):
    from PIL import Image
    points = [(quad[i] * im.width, quad[i + 1] * im.height) for i in range(0, 8, 2)]
    crosses = []
    for i in range(4):
        a, b, c = points[i], points[(i + 1) % 4], points[(i + 2) % 4]
        crosses.append((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]))
    if not (all(v > 0 for v in crosses) or all(v < 0 for v in crosses)):
        raise Problem("Perspective corners must form a convex TL,TR,BR,BL quadrilateral")
    width = round(max(math.dist(points[0], points[1]), math.dist(points[3], points[2])))
    height = round(max(math.dist(points[0], points[3]), math.dist(points[1], points[2])))
    if min(width, height) < 2:
        raise Problem("Perspective region is too small")
    # Solve the inverse homography: output rectangle -> source quadrilateral.
    matrix = []
    for (x, y), (u, v) in zip(((0, 0), (width, 0), (width, height), (0, height)), points):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y, u])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y, v])
    for col in range(8):
        pivot = max(range(col, 8), key=lambda row: abs(matrix[row][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        if abs(matrix[col][col]) < 1e-12:
            raise Problem("Degenerate perspective transform")
        divisor = matrix[col][col]
        matrix[col] = [v / divisor for v in matrix[col]]
        for row in range(8):
            if row != col:
                factor = matrix[row][col]
                matrix[row] = [a - factor * b for a, b in zip(matrix[row], matrix[col])]
    return im.transform((width, height), Image.Transform.PERSPECTIVE, tuple(row[8] for row in matrix), Image.Resampling.BICUBIC)


def prepare(args):
    from PIL import Image, ImageEnhance, ImageOps
    root, p = Path(args.project), project(args.project)
    if not (72 <= args.dpi <= 600 and 256 <= args.tile_size <= 4096 and 0 <= args.overlap < 0.5):
        raise Problem("Use DPI 72–600, tile size 256–4096, overlap 0–0.49")
    if args.quad and not all(math.isfinite(v) and 0 <= v <= 1 for v in args.quad):
        raise Problem("Quad coordinates must lie between 0 and 1")
    settings = {"dpi": args.dpi, "rotate": args.rotate, "quad": args.quad, "enhance": args.enhance,
                "tile_size": args.tile_size, "overlap": args.overlap, "exif_transpose": True}
    selected = [source_record(p, args.source)] if args.source else p["sources"]
    results = []
    for s in selected:
        inp = next(i for i in p["inputs"] if i["id"] == s["input_id"])
        if sha_file(inside(root, inp["path"])) != inp["sha256"]:
            raise Problem("Original file has changed: " + inp["path"])
        rev = digest({"input": inp["sha256"], "page": s["page"], "settings": settings})[:20]
        base = "prepared/%s/%s" % (s["id"], rev)
        dest = inside(root, base)
        metadata = dest / "metadata.json"
        if metadata.exists():
            from core import read_json
            saved = read_json(metadata)
            if not all(inside(root, f).is_file() for f in [saved["image"], saved["preview"]] + [t["path"] for t in saved["tiles"]]):
                raise Problem("Prepared revision is incomplete; retain it and prepare with new parameters: " + base)
            if sha_file(inside(root, saved["image"])) != saved.get("image_sha256"):
                raise Problem("Prepared full image was modified: " + base)
            s.update(saved)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = Path(tempfile.mkdtemp(prefix=".prepare-", dir=dest.parent))
            try:
                im = load_source(root, p, s, args.dpi, temp)
                raw_size = list(im.size)
                im.save(temp / "original-view.png")
                im = im.rotate(-args.rotate, expand=True)
                if args.quad:
                    im = perspective(im, args.quad)
                if args.enhance:
                    im = ImageEnhance.Contrast(ImageOps.autocontrast(im, cutoff=0.5)).enhance(1.15)
                im.save(temp / "full.png")
                preview = im.copy()
                preview.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
                preview.save(temp / "preview.png")
                tiles = []
                for y in positions(im.height, args.tile_size, args.overlap):
                    for x in positions(im.width, args.tile_size, args.overlap):
                        right, bottom = min(x + args.tile_size, im.width), min(y + args.tile_size, im.height)
                        name = "tile-%03d.png" % (len(tiles) + 1)
                        im.crop((x, y, right, bottom)).save(temp / name)
                        tiles.append({"path": base + "/" + name, "box": [x / im.width, y / im.height, right / im.width, bottom / im.height]})
                saved = {"revision": rev, "image": base + "/full.png", "preview": base + "/preview.png",
                         "image_sha256": sha_file(temp / "full.png"),
                         "size": list(im.size), "tiles": tiles, "transform": dict(settings, original_size=raw_size)}
                save_json(temp / "metadata.json", saved)
                temp.rename(dest)
                s.update(saved)
            finally:
                if temp.exists():
                    shutil.rmtree(temp)
        save_json(root / "project.json", p, backup=True)
        results.append(s)
    event(root, "prepare", {"sources": [s["id"] for s in selected]})
    return {"sources": results}


def crop(args):
    root, p = Path(args.project), project(args.project)
    s = source_record(p, args.source)
    if not s.get("revision") or not check_box(args.box):
        raise Problem("Prepare the source first; box must be x0 y0 x1 y1 within 0–1")
    name = identifier(args.name)
    rel = "assets/%s.png" % name
    path = inside(root, rel)
    if path.exists() or any(a["path"] == rel for a in p["assets"]):
        raise Problem("Asset already exists; choose a new name to preserve revisions")
    im = open_image(inside(root, s["image"]))
    box = [round(args.box[i] * (im.width if i % 2 == 0 else im.height)) for i in range(4)]
    if box[2] <= box[0] or box[3] <= box[1]:
        raise Problem("Crop has zero pixel area")
    im.crop(box).save(path)
    a = {"path": rel, "source_id": s["id"], "revision": s["revision"], "box": args.box, "sha256": sha_file(path)}
    p["assets"].append(a)
    save_json(root / "project.json", p, backup=True)
    event(root, "crop", a)
    return a


def add_unit(args):
    root, p = Path(args.project), project(args.project)
    uid = identifier(args.id)
    for sid in args.sources:
        source_record(p, sid)
    path = inside(root, "units/%s.json" % uid)
    if uid in p["units"] or path.exists():
        raise Problem("Unit already exists; edit its JSON without overwriting it")
    unit = empty_unit(uid, args.title, args.sources)
    save_json(path, unit)
    p["units"].append(uid)
    save_json(root / "project.json", p, backup=True)
    event(root, "unit", {"id": uid})
    return unit
