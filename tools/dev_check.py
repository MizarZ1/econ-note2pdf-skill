#!/usr/bin/env python3
"""Synthetic engineering smoke check. Does not assess transcription quality."""
import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "advanced-econ-note2pdf/scripts/econ_note.py"


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run(*args, expected=0):
    proc = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)
    if proc.returncode != expected:
        raise RuntimeError("%s returned %s, wanted %s\n%s\n%s" % (args, proc.returncode, expected, proc.stdout, proc.stderr))
    return json.loads(proc.stdout)


def check(base):
    image = Image.new("RGB", (1900, 1400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((200, 180, 1500, 1000), outline="navy", width=10)
    draw.text((250, 230), "Synthetic engineering fixture: x + y = 1", fill="black")
    photo = base / "board.png"
    image.save(photo)
    pdf = base / "pages.pdf"
    image.save(pdf, save_all=True, append_images=[image], resolution=300)
    root = base / "project"
    corrupt = base / "corrupt.pdf"
    corrupt.write_bytes(b"not a PDF")
    run("init", "--project", base / "rejected", "--inputs", corrupt, "--mode", "study", "--title", "bad input", expected=2)
    assert not (base / "rejected/project.json").exists()
    run("init", "--project", root, "--inputs", photo, pdf, "--mode", "both", "--title", "工程自检", "--domains", "math")
    run("init", "--project", root, "--inputs", photo, "--mode", "study", "--title", "refuse overwrite", expected=2)
    p = json.loads((root / "project.json").read_text())
    assert len(p["sources"]) == 3
    run("validate", "--project", root, expected=3)
    run("prepare", "--project", root, "--tile-size", "1024")
    before = (root / "project.json").read_bytes()
    run("prepare", "--project", root, "--tile-size", "1024")
    assert (root / "project.json").read_bytes() == before, "prepare must be idempotent"
    p = json.loads(before)
    assert all(len(s["tiles"]) > 1 for s in p["sources"])
    asset = run("crop", "--project", root, "--source", "s0001", "--box", ".1", ".1", ".9", ".9", "--name", "diagram")
    assert (root / asset["path"]).is_file()
    run("crop", "--project", root, "--source", "s0001", "--box", ".1", ".1", ".9", ".9", "--name", "diagram", expected=2)
    for i, source in enumerate(p["sources"], 1):
        uid, bid = "u%03d" % i, "b%03d" % i
        ref = {"source_id": source["id"], "revision": source["revision"], "box": [0, 0, 1, 1]}
        fragment = "content/%s.tex" % bid
        (root / fragment).write_text("\\[x+y=1\\]\n", encoding="utf-8")
        unit = {"id": uid, "title": "合成内容 %s" % i, "source_ids": [source["id"]],
                "coverage": [{"id": "c001", **ref, "kind": "equation", "disposition": "included", "block_ids": [bid], "reason": ""}],
                "blocks": [{"id": bid, "kind": "equation", "origin": "source", "refs": [ref], "body": {"faithful": fragment}}], "issues": []}
        write(root / "units" / (uid + ".json"), unit)
    run("validate", "--project", root)
    run("review", "--project", root, "--kind", "content", "--unit", "u001", "--note", "Synthetic state-transition check; not an OCR evaluation")
    assert run("status", "--project", root)["units"][0]["content_review_current"]
    (root / "content/b001.tex").write_text("\\[x+y=2\\]\n", encoding="utf-8")
    assert not run("status", "--project", root)["units"][0]["content_review_current"]
    run("prepare", "--project", root, "--source", "s0001", "--rotate", "90", "--tile-size", "1024")
    result = run("validate", "--project", root, expected=2)
    assert any("Stale" in e or "stale" in e for e in result["errors"])
    run("prepare", "--project", root, "--source", "s0001", "--tile-size", "1024")
    run("validate", "--project", root)
    bad = json.loads((root / "units/u001.json").read_text())
    saved = json.loads(json.dumps(bad))
    bad["blocks"][0]["body"]["faithful"] = "../outside.tex"
    write(root / "units/u001.json", bad)
    assert run("validate", "--project", root, expected=2)["errors"]
    write(root / "units/u001.json", saved)
    print("PASS: import, PDF pages, immutable originals, tiles, crop collisions, state invalidation, stale sources, path confinement")
    return root


def check_modes(root):
    path = root / "units/u001.json"
    original = json.loads(path.read_text())
    unit = json.loads(json.dumps(original))
    extra = root / "content/study-extra.tex"
    extra.write_text("STUDY-ONLY-MARKER\n", encoding="utf-8")
    try:
        unit["blocks"].append({"id": "extra001", "kind": "text", "origin": "explanation", "refs": [], "body": {"study": "content/study-extra.tex"}})
        unit["issues"] = [{"id": "note001", "severity": "note", "status": "open", "block_ids": ["b001"],
                           "summary": "APPENDIX-ONLY-MARKER", "detail": "Synthetic placement check"}]
        write(path, unit)
        run("assemble", "--project", root, "--mode", "faithful")
        assert "STUDY-ONLY-MARKER" not in (root / "build/faithful/units/u001.tex").read_text()
        run("assemble", "--project", root, "--mode", "study")
        assert "STUDY-ONLY-MARKER" in (root / "build/study/units/u001.tex").read_text()
        assert "APPENDIX-ONLY-MARKER" not in (root / "build/study/units/u001.tex").read_text()
        assert "APPENDIX-ONLY-MARKER" in (root / "build/study/appendix.tex").read_text()
        unit["issues"].append({"id": "critical001", "severity": "critical", "status": "open", "block_ids": ["b001"],
                               "summary": "BODY-CRITICAL-MARKER", "detail": "Synthetic missing condition", "appendix": False})
        write(path, unit)
        run("assemble", "--project", root, "--mode", "study", expected=2)
        result = run("assemble", "--project", root, "--mode", "study", "--allow-partial", expected=3)
        assert result["partial"] and "BODY-CRITICAL-MARKER" in (root / "build/study/units/u001.tex").read_text()
    finally:
        write(path, original)
        extra.unlink()
    run("validate", "--project", root)
    print("PASS: faithful/study separation, ordinary appendix placement, and critical partial-output policy")


def check_latex(root):
    p = json.loads((root / "project.json").read_text())
    p["symbols"] = [{"tex": "c_t", "meaning": "第 t 期消费", "scope": "跨期模型"},
                    {"tex": r"\beta", "meaning": "贴现因子", "scope": "跨期模型"}]
    p["preamble"] = "content/course.tex"
    (root / p["preamble"]).write_text(r"\newcommand{\CourseR}{\mathbb{R}}" + "\n", encoding="utf-8")
    write(root / "project.json", p)
    (root / "content/b001.tex").write_text(r"""\subsection{问题、条件与结论}
以下为合成排版材料，用于检查中文、公式与交叉引用，不代表任何真实课程转录。
设消费与储蓄均处于内点，效用可微，回报与信息集按给定模型定义。
\begin{align}
 c_t+a_{t+1} &= y_t+R_t a_t, \label{eq:budget}\\
 u'(c_t)&=\beta\EconE_t\bigl[R_{t+1}u'(c_{t+1})\bigr].
\end{align}
第一式为预算约束，第二式用于演示含条件期望的跨期最优条件排版。
\begin{proposition}本例仅检查环境编号与数学排版。\end{proposition}
\begin{proof}由给定条件进行相应运算，保持所有时间下标。\end{proof}
""", encoding="utf-8")
    (root / "content/b002.tex").write_text(r"""\subsection{示意图与来源裁切}
式~\eqref{eq:budget} 展示跨章节引用。下面的预算线仅是指定函数的排版示例。
\begin{figure}[htbp]\centering
\begin{tikzpicture}
\begin{axis}[width=.68\linewidth,height=5cm,axis lines=left,xlabel={$x_1$},ylabel={$x_2$},xmin=0,xmax=5,ymin=0,ymax=5]
\addplot[domain=0:4,thick,blue]{4-x};
\node at (axis cs:2.7,2.7) {$p_1x_1+p_2x_2=m$};
\end{axis}\end{tikzpicture}
\caption{合成预算线示意}\end{figure}
\begin{figure}[htbp]\centering
\includegraphics[width=.42\linewidth]{assets/diagram.png}
\caption{合成来源区域，检查裁切与比例}\end{figure}
""", encoding="utf-8")
    (root / "content/b003.tex").write_text(r"""\subsection{回归表与矩阵}
本表为排版示例，不含实际估计结果；括号行演示标准误位置。
\begin{table}[htbp]\centering
\caption{合成回归表}
\begin{tabular}{lrr}\toprule 变量 & 模型一 & 模型二 \\\midrule
解释变量 & 0.120 & 0.105 \\
 & (0.030) & (0.040) \\
样本量 & 100 & 100 \\\bottomrule
\end{tabular}
\par\smallskip{\small 注：所有数字均为合成占位值；此例不演示显著性标记。}
\end{table}
\[\widehat\beta=(X^{\mathsf T}X)^{-1}X^{\mathsf T}y,\qquad
 X=\begin{bmatrix}1&x_1\\1&x_2\end{bmatrix}.\]
上述估计式在矩阵满足相应可逆条件时使用，变量取值于 $\CourseR$。
""", encoding="utf-8")
    unit = json.loads((root / "units/u001.json").read_text())
    unit["issues"] = [{"id": "n001", "severity": "note", "status": "open", "block_ids": ["b001"],
                       "summary": "符号说明示例", "detail": "本条用于检查普通事项只出现在附录。"}]
    write(root / "units/u001.json", unit)
    run("validate", "--project", root)
    run("assemble", "--project", root, "--mode", "study")
    built = run("compile", "--project", root, "--mode", "study")
    assert built["compiled"] and not built["partial"]
    run("render", "--project", root, "--mode", "study")
    run("package", "--project", root, "--mode", "study", expected=2)
    packed = run("package", "--project", root, "--mode", "study", "--allow-unreviewed", expected=3)
    assert packed["status"] == "unreviewed"
    with zipfile.ZipFile(packed["project_zip"]) as z:
        assert "main.pdf" in z.namelist() and "source-map.json" in z.namelist()
        assert not any(name.startswith(("originals/", "logs/")) for name in z.namelist())
    # Snapshot clean pages for actual visual inspection after failure-path checks.
    import shutil
    shutil.copytree(root / "previews/study", root.parent / "clean-previews")
    saved = (root / "content/b003.tex").read_text()
    (root / "content/b003.tex").write_text(saved + "\n\\UndefinedEngineeringCommand\n")
    run("compile", "--project", root, "--mode", "study", expected=2)  # stale build
    run("assemble", "--project", root, "--mode", "study")
    failed = run("compile", "--project", root, "--mode", "study", expected=2)
    assert not failed["compiled"] and not (root / "build/study/main.pdf").exists()
    isolated = run("compile", "--project", root, "--mode", "study", "--isolate-failures", expected=3)
    assert isolated["failed_units"] == ["u003"] and isolated["partial"]
    assert (root / "build/study/uncompiled/u003.tex").is_file()
    (root / "content/b003.tex").write_text(saved, encoding="utf-8")
    run("assemble", "--project", root, "--mode", "study")
    run("compile", "--project", root, "--mode", "study")
    run("render", "--project", root, "--mode", "study")
    run("package", "--project", root, "--mode", "study", "--allow-unreviewed", expected=3)
    print("PASS: LaTeX, Chinese/math/figures/tables, references, render, package gate, stale PDF rejection, failed-unit isolation and recovery")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=Path, help="Keep synthetic artifacts in a new or empty directory")
    parser.add_argument("--with-latex", action="store_true", help="Exercise the synthetic compile/render/delivery chain")
    args = parser.parse_args()
    if args.keep:
        args.keep.mkdir(parents=True, exist_ok=True)
        if any(args.keep.iterdir()):
            parser.error("--keep directory must be empty")
        root = check(args.keep.resolve())
        check_modes(root)
        if args.with_latex:
            check_latex(root)
    else:
        with tempfile.TemporaryDirectory(prefix="econ-dev-") as tmp:
            root = check(Path(tmp))
            check_modes(root)
            if args.with_latex:
                check_latex(root)


if __name__ == "__main__":
    main()
