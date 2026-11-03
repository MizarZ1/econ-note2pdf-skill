#!/usr/bin/env python3
"""Synthetic CJK PDF regression; requires XeLaTeX and TeX CMaps, no user files."""
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import TextStringObject, NameObject

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "advanced-econ-note2pdf/scripts"))
from pdf_compat import ensure_unicode_maps


def main():
    with tempfile.TemporaryDirectory(prefix="econ-unicode-check-") as directory:
        root = Path(directory)
        (root / "main.tex").write_text(r"""\documentclass[fontset=fandol]{ctexart}
\usepackage{hyperref}
\hypersetup{pdftitle={中文兼容检查},pdfauthor={Synthetic fixture}}
\begin{document}
\section{中文标题}
中文正文：状态变量、控制变量和边界条件。
\[H=f+\lambda g\]
\end{document}
""", encoding="utf-8")
        for _ in range(2):
            result = subprocess.run(["xelatex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=root, capture_output=True)
            if result.returncode:
                raise RuntimeError(result.stdout.decode(errors="replace")[-3000:])
        pdf = root / "main.pdf"
        before = PdfReader(pdf)
        metadata = dict(before.metadata)
        outline = [(v.title, before.get_destination_page_number(v)) for v in before.outline]
        count = len(before.pages)
        result = ensure_unicode_maps(pdf)
        assert not result["diagnostics"], result
        after = PdfReader(pdf)
        assert len(after.pages) == count and dict(after.metadata) == metadata
        assert [(v.title, after.get_destination_page_number(v)) for v in after.outline] == outline
        assert "中文正文" in "".join(p.extract_text() for p in after.pages)
        for page in after.pages:
            for ref in page["/Resources"]["/Font"].values():
                font = ref.get_object()
                if "Fandol" in str(font.get("/BaseFont", "")):
                    assert "/ToUnicode" in font
        snapshot = hashlib.sha256(pdf.read_bytes()).digest()
        assert ensure_unicode_maps(pdf) == {"fonts_patched": 0, "diagnostics": []}
        assert hashlib.sha256(pdf.read_bytes()).digest() == snapshot
        # Unsupported collections must not be falsely assigned an Adobe GB1 map.
        writer = PdfWriter()
        writer.clone_document_from_reader(after)
        for page in writer.pages:
            for ref in page["/Resources"]["/Font"].values():
                font = ref.get_object()
                if "Fandol" in str(font.get("/BaseFont", "")):
                    del font["/ToUnicode"]
                    info = font["/DescendantFonts"][0].get_object()["/CIDSystemInfo"]
                    info[NameObject("/Ordering")] = TextStringObject("UnknownCollection")
        unsupported = root / "unsupported.pdf"
        writer.write(unsupported)
        previous = unsupported.read_bytes()
        result = ensure_unicode_maps(unsupported)
        assert result["fonts_patched"] == 0 and result["diagnostics"]
        assert unsupported.read_bytes() == previous
    print("PASS: CJK Unicode maps, text extraction, metadata/bookmarks, idempotence, unknown collection refusal")


if __name__ == "__main__":
    main()
