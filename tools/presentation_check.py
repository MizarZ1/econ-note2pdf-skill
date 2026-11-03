#!/usr/bin/env python3
"""Synthetic presentation regression; requires XeLaTeX and local PDF tools."""
import json
import re
import tempfile
from pathlib import Path

from pypdf import PdfReader
from dev_check import check, run, write


def text_colors(pdf, markers):
    """Track PDF fill color at text-show operators, not generated TeX wrappers."""
    found = {marker: [] for marker in markers}
    for page in pdf.pages:
        color = (0.0, 0.0, 0.0)
        stack = []
        last_text_color = color

        def before(operator, operands, cm, tm):
            nonlocal color, last_text_color
            if operator == b"q":
                stack.append(color)
            elif operator == b"Q":
                color = stack.pop() if stack else (0.0, 0.0, 0.0)
            elif operator == b"rg":
                color = tuple(float(v) for v in operands)
            elif operator == b"g":
                color = (float(operands[0]),) * 3
            elif operator == b"k":
                cyan, magenta, yellow, black = map(float, operands)
                color = tuple(1 - min(1, v + black) for v in (cyan, magenta, yellow))
            elif operator in (b"cs", b"sc", b"scn"):
                color = None  # Never silently accept an unhandled color space.
            if operator in (b"Tj", b"TJ", b"'", b'"'):
                last_text_color = color

        def visit(text, cm, tm, font, size):
            for marker in markers:
                if re.search(r"(?<![A-Za-z])" + re.escape(marker) + r"(?![A-Za-z])", text):
                    found[marker].append(last_text_color)

        page.extract_text(visitor_operand_before=before, visitor_text=visit)
    return found


def assert_colors(pdf, style):
    source_markers = ("FIGUREBODYMARKER", "FIGUREMARKER", "TABLEMARKER", "TABLECAPTIONMARKER", "LONGTABLEMARKER", "LONGTABLECAPTIONMARKER")
    expected = {marker: tuple(int(v, 16) / 255 for v in ("23", "4F", "78")) for marker in source_markers}
    expected["EXPLANATIONMARKER"] = (0.0, 0.0, 0.0)
    colors = text_colors(pdf, expected)
    for marker, rgb in expected.items():
        assert colors[marker], (style, "PDF text marker not located", marker)
        assert all(value is not None and len(value) == 3 and all(abs(a - b) < .002 for a, b in zip(value, rgb))
                   for value in colors[marker]), (style, marker, colors[marker], rgb)


def main():
    with tempfile.TemporaryDirectory(prefix="econ-presentation-") as directory:
        root = check(Path(directory))
        project_path = root / "project.json"
        project = json.loads(project_path.read_text())
        first = root / "content/b001.tex"
        paragraphs = ["SOURCESTART\\par"]
        paragraphs += ["段落 %d：状态变量与控制变量需要结合约束和边界条件分析。\\par" % i for i in range(1, 81)]
        paragraphs += ["SOURCEEND\\par"]
        first.write_text("\n".join(paragraphs), encoding="utf-8")
        (root / "content/explanation.tex").write_text("EXPLANATIONMARKER\\par 补充讲解连接条件与结论。\n", encoding="utf-8")
        unit_path = root / "units/u001.json"
        unit = json.loads(unit_path.read_text())
        unit["blocks"].append({"id": "explanation001", "kind": "text", "origin": "explanation", "refs": [],
                                "body": {"study": "content/explanation.tex"}})
        write(unit_path, unit)
        (root / "content/b002.tex").write_text(r"""\begin{figure}[htbp]\centering
\includegraphics[width=.3\linewidth]{assets/diagram.png}\par FIGUREBODYMARKER\par
\caption{FIGUREMARKER}\end{figure}
""", encoding="utf-8")
        (root / "content/b003.tex").write_text(r"""\begin{table}[htbp]\centering
\begin{tabular}{lr}TABLEMARKER & 1\end{tabular}\caption{TABLECAPTIONMARKER}\end{table}
\begin{longtable}{lr}\caption{LONGTABLECAPTIONMARKER}\\ LONGTABLEMARKER & 2\\\end{longtable}
""", encoding="utf-8")
        # Projects created before presentation settings remain valid and plain.
        project.pop("presentation", None)
        write(project_path, project)
        run("validate", "--project", root)
        run("assemble", "--project", root, "--mode", "study")
        legacy = (root / "build/study/units/u001.tex").read_text()
        assert "EconSourceBox" not in legacy and "color{EconSource}" not in legacy
        assert "复习讲义" in (root / "build/study/main.tex").read_text()
        project["presentation"] = {"purpose": "revision", "source_style": "plain"}
        write(project_path, project)
        run("validate", "--project", root)
        run("assemble", "--project", root, "--mode", "study")
        plain = (root / "build/study/units/u001.tex").read_text()
        assert all(marker in plain for marker in ("SOURCESTART", "SOURCEEND", "EXPLANATIONMARKER"))
        assert "EconSourceBox" not in plain and "color{EconSource}" not in plain
        # A style change invalidates the already assembled project.
        project["presentation"]["source_style"] = "accent"
        write(project_path, project)
        stale = run("compile", "--project", root, "--mode", "study", expected=2)
        assert "stale" in stale["error"].lower()
        for key, value in (("purpose", "unknown"), ("source_style", "red")):
            saved = project["presentation"][key]
            project["presentation"][key] = value
            write(project_path, project)
            result = run("validate", "--project", root, expected=2)
            assert any("presentation." + key in msg for msg in result["errors"])
            project["presentation"][key] = saved
        for style, purpose in (("accent", "revision"), ("box", "reference")):
            project["presentation"] = {"purpose": purpose, "source_style": style}
            write(project_path, project)
            run("assemble", "--project", root, "--mode", "study")
            run("compile", "--project", root, "--mode", "study")
            pdf = PdfReader(root / "build/study/main.pdf")
            text = "\n".join(page.extract_text() for page in pdf.pages)
            for marker in ("SOURCESTART", "SOURCEEND", "EXPLANATIONMARKER", "FIGUREMARKER", "TABLEMARKER", "LONGTABLEMARKER"):
                assert marker in text, (style, marker)
            assert_colors(pdf, style)
            assert len(pdf.pages) >= 3, "The source block must exercise page breaking"
            assert ("参考资料" if purpose == "reference" else "复习讲义") in text
            if style == "box":
                # Floats/long tables retain their native layout; source prose uses a breakable box.
                assert "EconSourceBox" in (root / "build/study/units/u001.tex").read_text()
                for uid in ("u002", "u003"):
                    rendered = (root / ("build/study/units/%s.tex" % uid)).read_text()
                    assert "EconSourceBox" not in rendered and "color{EconSource}" in rendered
            print("PASS: %s retains long source and blue figure/table/captions with black explanation (%d pages)" % (style, len(pdf.pages)))
        run("assemble", "--project", root, "--mode", "faithful")
        faithful_main = (root / "build/faithful/main.tex").read_text()
        assert "忠实转录" in faithful_main and "参考资料" not in faithful_main
        faithful = (root / "build/faithful/units/u001.tex").read_text()
        assert "SOURCEEND" in faithful and "EXPLANATIONMARKER" not in faithful
    print("PASS: plain compatibility, stale presentation, invalid configuration, reference/study and faithful separation")


if __name__ == "__main__":
    main()
