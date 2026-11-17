#!/usr/bin/env python3
"""Check a portable skill ZIP in isolated layouts; no host/model calls or user installs."""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image

from package_skill import SKILL, package


def run(cli, cwd, *args, expected=0):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)  # Do not let checkout modules mask missing bundled imports.
    result = subprocess.run(
        [sys.executable, str(cli), *map(str, args)], cwd=cwd, env=env,
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != expected:
        raise RuntimeError("%s returned %s, expected %s\n%s\n%s" %
                           (args, result.returncode, expected, result.stdout, result.stderr))
    return json.loads(result.stdout)


def inspect_bundle(bundle):
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        assert len(names) == len(set(names)), "Duplicate archive entries"
        required = ("SKILL.md", "LICENSE", "requirements.txt", "scripts/econ_note.py",
                    "scripts/pdf_compat.py", "assets/latex/preamble.tex")
        assert all(SKILL.name + "/" + name in names for name in required)
        # The maintained entry uses single-line, unquoted metadata; check the
        # uploaded bytes rather than relying on the source checkout's frontmatter.
        entry = archive.read(SKILL.name + "/SKILL.md").decode("utf-8")
        parts = entry.split("---", 2)
        assert len(parts) == 3 and not parts[0].strip(), "Missing ZIP frontmatter"
        name = re.search(r"^name: ([a-z0-9-]+)$", parts[1], re.M)
        description = re.search(r"^description: ([^\r\n]+)$", parts[1], re.M)
        assert name and name[1] == SKILL.name and len(name[1]) <= 64
        assert description and 1 <= len(description[1].strip()) <= 200
        for entry in entries:
            path = PurePosixPath(entry.filename)
            assert not path.is_absolute() and ".." not in path.parts
            assert "\\" not in entry.filename and path.parts[0] == SKILL.name
            assert stat.S_ISREG(entry.external_attr >> 16), "ZIP must contain regular files"
        return {entry.filename: hashlib.sha256(archive.read(entry)).hexdigest() for entry in entries}


def check_layout(bundle, manifest, directory, fixture, with_latex):
    skill_root = directory / SKILL.name
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(directory)
    for name, expected in manifest.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    for path in skill_root.rglob("*.md"):
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (path.parent / target.split("#")[0]).exists(), "Missing bundled reference: " + target

    # Run away from both the checkout and the installed skill, using paths with spaces.
    cwd = directory.parent / "unrelated working directory"
    cwd.mkdir()
    project = cwd / "course project"
    cli = skill_root / "scripts/econ_note.py"
    assert not run(cli, cwd, "doctor")["required_missing"]
    run(cli, cwd, "init", "--project", project, "--inputs", fixture,
        "--mode", "study", "--title", "安装自检", "--domains", "math")
    run(cli, cwd, "prepare", "--project", project)
    metadata = json.loads((project / "project.json").read_text(encoding="utf-8"))
    source = metadata["sources"][0]
    ref = {"source_id": source["id"], "revision": source["revision"], "box": [0, 0, 1, 1]}
    fragment = "content/b001.tex"
    (project / fragment).write_text("安装工程自检，非课程转录。\\[x+y=1\\]\n", encoding="utf-8")
    unit = {
        "id": "u001", "title": "独立安装资源检查", "source_ids": [source["id"]],
        "coverage": [{"id": "c001", **ref, "kind": "equation", "disposition": "included",
                      "block_ids": ["b001"], "reason": ""}],
        "blocks": [{"id": "b001", "kind": "equation", "origin": "source", "refs": [ref],
                    "body": {"faithful": fragment}}], "issues": [],
    }
    (project / "units/u001.json").write_text(json.dumps(unit, ensure_ascii=False), encoding="utf-8")
    run(cli, cwd, "validate", "--project", project)
    assembled = run(cli, cwd, "assemble", "--project", project, "--mode", "study")
    assert not assembled["partial"]
    template = project / "build/study/preamble.tex"
    assert template.read_bytes() == (skill_root / "assets/latex/preamble.tex").read_bytes()

    if with_latex:
        result = run(cli, cwd, "compile", "--project", project, "--mode", "study")
        assert result["compiled"] and not result["partial"]
        assert run(cli, cwd, "render", "--project", project, "--mode", "study")["pages"]
        result = run(cli, cwd, "package", "--project", project, "--mode", "study",
                     "--allow-unreviewed", expected=3)
        assert result["status"] == "unreviewed" and Path(result["pdf"]).is_file()
        assert not result["content_reviewed"] and not result["layout_reviewed"]
        with zipfile.ZipFile(result["project_zip"]) as delivery:
            assert delivery.read("LICENSE") == (skill_root / "LICENSE").read_bytes()
            assert delivery.read("pdf_compat.py") == (skill_root / "scripts/pdf_compat.py").read_bytes()
    # A run may write its project, but must not modify the installed skill.
    assert {p.relative_to(directory).as_posix() for p in skill_root.rglob("*") if p.is_file()} == set(manifest)
    for name, expected in manifest.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-latex", action="store_true", help="Also compile, render, and export an unreviewed synthetic PDF")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="econ-installation-") as tmp:
        base = Path(tmp)
        first = package(base / "skill.zip")
        second = package(base / "repeat.zip")
        assert first["sha256"] == second["sha256"], "Packaging is not reproducible"
        manifest = inspect_bundle(base / "skill.zip")
        fixture = base / "synthetic board.png"
        Image.new("RGB", (80, 60), "white").save(fixture)
        for host in (".claude", ".dsh", ".agents"):
            check_layout(base / "skill.zip", manifest, base / host / "skills", fixture, args.with_latex)
    print("PASS: reproducible ZIP, upload metadata, complete references, isolated .claude/.dsh/.agents layouts, "
          "external cwd, template lookup, and unchanged installed files" +
          ("; synthetic PDF compiled/rendered/exported (unreviewed)" if args.with_latex else ""))
    print("Scope: package and local execution only; host discovery, upload, model behavior, and reading quality not tested.")


if __name__ == "__main__":
    main()
