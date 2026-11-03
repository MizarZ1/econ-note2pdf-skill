#!/usr/bin/env python3
"""Package only reusable skill resources, never project inputs or outputs."""
import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "advanced-econ-note2pdf"


def package(destination):
    allowed_roots = {"scripts", "references", "assets", "agents"}
    allowed_suffixes = {".py", ".md", ".tex", ".yaml", ".json", ".txt"}
    files = []
    for path in sorted(SKILL.rglob("*")):
        rel = path.relative_to(SKILL)
        if path.is_file() and not path.is_symlink() and "__pycache__" not in rel.parts:
            if (rel.as_posix() in ("SKILL.md", "requirements.txt", "LICENSE") or rel.parts[0] in allowed_roots) and (path.suffix in allowed_suffixes or rel.as_posix() == "LICENSE"):
                files.append(path)
    if SKILL / "SKILL.md" not in files:
        raise RuntimeError("Missing skill entry point")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".skill-", suffix=".zip", dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                rel = Path(SKILL.name) / path.relative_to(SKILL)
                info = zipfile.ZipInfo(rel.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    sha = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(sha + "  " + destination.name + "\n")
    return {"path": str(destination.resolve()), "files": len(files), "sha256": sha}


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPO / "dist/advanced-econ-note2pdf-v0.1.zip")
    print(json.dumps(package(parser.parse_args().output), ensure_ascii=False, indent=2))
