#!/usr/bin/env python3
"""Portable static repository checks; no external services or course inputs."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "advanced-econ-note2pdf"


def main():
    errors = []
    if (ROOT / "LICENSE").read_bytes() != (SKILL / "LICENSE").read_bytes():
        errors.append("Repository and bundled skill license differ")
    entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    parts = entry.split("---", 2)
    if len(parts) != 3 or not re.search(r"^name: advanced-econ-note2pdf$", parts[1], re.M) or not re.search(r"^description: .+", parts[1], re.M):
        errors.append("Invalid skill frontmatter")
    paths = list(ROOT.glob("*.md"))
    for directory in (SKILL, ROOT / "docs", ROOT / "tools", ROOT / ".github"):
        paths.extend(p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for path in paths:
        if path.suffix not in (".md", ".py", ".tex", ".yaml", ".yml", ".txt"):
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".md" and "[TODO:" in text:
            errors.append(str(path) + ": generator placeholder")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=str(path))
            except SyntaxError as exc:
                errors.append(str(exc))
        if path.suffix == ".md":
            if text.count("```") % 2:
                errors.append(str(path) + ": unbalanced code fence")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if "://" not in target and not target.startswith("#") and not (path.parent / target.split("#")[0]).exists():
                    errors.append(str(path) + ": missing link " + target)
    for host in (".agents", ".claude"):
        path = ROOT / host / "skills" / SKILL.name
        if not path.exists() or path.resolve() != SKILL.resolve():
            errors.append(host + ": invalid common skill link")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: skill metadata, Python syntax, Markdown links, fences, and host links")


if __name__ == "__main__":
    main()
