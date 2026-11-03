"""Embed missing standard CJK ToUnicode maps for self-contained PDF readers.

This changes neither glyphs nor layout. Existing Unicode maps are preserved.
"""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DecodedStreamObject

COLLECTIONS = {"GB1", "CNS1", "Japan1", "Korea1", "KR"}


def _fonts(writer):
    """Walk page and nested Form resources, without revisiting shared objects."""
    seen_resources, seen_fonts = set(), set()

    def visit(reference):
        resources = reference.get_object() if reference is not None else {}
        if id(resources) in seen_resources:
            return
        seen_resources.add(id(resources))
        fonts = resources.get("/Font", {})
        fonts = fonts.get_object() if hasattr(fonts, "get_object") else fonts
        for ref in fonts.values():
            font = ref.get_object()
            if id(font) not in seen_fonts:
                seen_fonts.add(id(font))
                yield font
        objects = resources.get("/XObject", {})
        objects = objects.get_object() if hasattr(objects, "get_object") else objects
        for ref in objects.values():
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Form":
                yield from visit(obj.get("/Resources"))

    for page in writer.pages:
        yield from visit(page.get("/Resources"))


def _mapping(collection):
    name = "Adobe-%s-UCS2" % collection
    if not shutil.which("kpsewhich"):
        raise ValueError("kpsewhich is unavailable; install TeX adobemapping resources")
    result = subprocess.run(["kpsewhich", "--format=cmap", name],
                            capture_output=True, text=True, timeout=15)
    location = result.stdout.strip()
    if result.returncode or not location or not Path(location).is_file():
        raise ValueError("Missing TeX CMap " + name + "; install adobemapping")
    path = Path(location)
    if path.stat().st_size > 2_000_000:
        raise ValueError("CMap exceeds the supported size: " + name)
    raw = path.read_bytes()
    text = re.sub(rb"%[^\r\n]*", b"", raw)
    if (re.search(rb"\busecmap\b", text)
            or not re.search(rb"/CMapType\s+2\s+def\b", text)
            or not re.search(rb"\bbeginbf(?:char|range)\b", text)
            or not re.search(rb"/CMapName\s+/" + re.escape(name.encode()) + rb"\s+def\b", text)):
        raise ValueError("CMap is not a matching self-contained Unicode map: " + name)
    return raw


def ensure_unicode_maps(pdf_path):
    """Atomically patch supported missing maps; return counts and diagnostics.

    Unsupported or unavailable maps are reported rather than guessed. The caller
    should retain those diagnostics in build state and avoid claiming that all
    readers have been verified. Existing bookmarks, metadata and fonts are cloned.
    """
    path = Path(pdf_path)
    diagnostics = []
    patched = 0
    with path.open("rb") as source:
        reader = PdfReader(source)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        streams = {}
        failed = set()
        for font in _fonts(writer):
            if font.get("/Subtype") != "/Type0" or "/ToUnicode" in font:
                continue
            label = str(font.get("/BaseFont", "unnamed font"))
            descendants = font.get("/DescendantFonts", [])
            if font.get("/Encoding") not in ("/Identity-H", "/Identity-V") or len(descendants) != 1:
                diagnostics.append("Missing ToUnicode with unsupported encoding: " + label)
                continue
            info = descendants[0].get_object().get("/CIDSystemInfo", {})
            info = info.get_object() if hasattr(info, "get_object") else info
            collection = str(info.get("/Ordering", ""))
            if str(info.get("/Registry", "")) != "Adobe" or collection not in COLLECTIONS:
                diagnostics.append("Missing ToUnicode with unsupported CID collection: " + label)
                continue
            if collection in failed:
                continue
            if collection not in streams:
                try:
                    stream = DecodedStreamObject()
                    stream.set_data(_mapping(collection))
                    streams[collection] = writer._add_object(stream.flate_encode())
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    diagnostics.append(str(exc))
                    failed.add(collection)
                    continue
            font[NameObject("/ToUnicode")] = streams[collection]
            patched += 1
        if patched:
            fd, temp = tempfile.mkstemp(prefix=".unicode-", suffix=".pdf", dir=path.parent)
            try:
                with os.fdopen(fd, "wb") as target:
                    writer.write(target)
                    target.flush()
                    os.fsync(target.fileno())
                os.chmod(temp, path.stat().st_mode & 0o777)
                source.close()  # Windows cannot replace a file with an open reader handle.
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
    return {"fonts_patched": patched, "diagnostics": diagnostics}


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    outcome = ensure_unicode_maps(args.pdf)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(3 if outcome["diagnostics"] else 0)
