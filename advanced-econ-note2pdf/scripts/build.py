"""Assemble reproducible LaTeX projects, compile, render, and package."""
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import zipfile
from pathlib import Path

from core import (Problem, body_path, digest, fingerprint, inside, now, project,
                  save_json, sha_file, state, token, unit_digest, units)
from model import TEMPLATES, validate

DOCUMENT_CLASS = r"\documentclass[UTF8,a4paper,11pt,fontset=fandol]{ctexart}"


def tex_escape(value):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in str(value))


def mode_check(p, mode):
    if p["mode"] != "both" and p["mode"] != mode:
        raise Problem("Requested mode differs from project mode")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def source_digest(directory):
    files = {}
    for f in sorted(Path(directory).rglob("*")):
        rel = f.relative_to(directory).as_posix()
        if f.is_file() and (f.suffix == ".tex" or rel.startswith("assets/") or rel == "source-map.json"):
            files[rel] = sha_file(f)
    return digest(files)


def heading(unit):
    return "\\section{%s}\\label{unit:%s}\n" % (tex_escape(unit["title"]), unit["id"])


def render_unit(root, unit, mode, source_style="plain"):
    lines = [heading(unit)]
    visible = [b for b in unit["blocks"] if not (b["origin"] == "explanation" and mode == "faithful")]
    if not visible:
        if unit["coverage"] and all(c["disposition"] in ("excluded", "duplicate") for c in unit["coverage"]):
            return ""
        lines.append("\\EconMissing{本节材料尚未完成转录。}\n")
    for block in visible:
        lines.append("\\phantomsection\\label{block:%s}\n" % block["id"])
        for issue in unit["issues"]:
            if issue["severity"] == "critical" and issue["status"] == "open" and block["id"] in issue["block_ids"]:
                lines.append("\\EconMissing{%s}\n" % tex_escape(issue["summary"]))
        path = body_path(block, mode)
        text = inside(root, path).read_text(encoding="utf-8") if path else ""
        if not re.sub(r"(?m)(?<!\\)%.*$", "", text).strip():
            text = "\\EconMissing{此处原始内容尚未完成转录。}\n"
        if block["origin"] == "source" and source_style != "plain":
            # Floats and captions reset color; keep both settings local to the float.
            caption_color = r"\captionsetup{font+={color=EconSource},labelfont+={color=EconSource}}"
            text = re.sub(r"(\\begin\s*\{(?:figure|table)\*?\}(?:\s*\[[^\]]*\])?)",
                          lambda match: match.group(1) + r"\color{EconSource}" + caption_color, text)
            # Keep longtable's position/column arguments next to its begin command.
            text = re.sub(r"\\begin\s*\{longtable\}", lambda match: caption_color + match.group(0), text)
            # Floating/long tables keep their own pagination; only tint their contents.
            boxed = source_style == "box" and not re.search(r"\\begin\s*\{(?:figure|table|longtable)\*?\}", text)
            if boxed:
                text = "\\begin{EconSourceBox}\n" + text + "\n\\end{EconSourceBox}"
            else:
                text = "\\begingroup\\color{EconSource}\n" + text + "\n\\par\\endgroup"
        lines.append("%% source-block: %s\n%s\n\n" % (block["id"], text))
    return "".join(lines)


def appendix(all_units, mode):
    lines, used = [], set()
    for unit in all_units:
        visible = {b["id"] for b in unit["blocks"] if not (b["origin"] == "explanation" and mode == "faithful")}
        for issue in unit["issues"]:
            critical = issue["severity"] == "critical" and issue["status"] == "open"
            if not critical and issue.get("appendix") is False:
                continue
            links = [b for b in issue["block_ids"] if b in visible]
            if issue["block_ids"] and not links:
                continue
            location = "\\hyperref[block:%s]{对应位置}" % links[0] if links else tex_escape(unit["title"])
            lines.append("\\paragraph{%s} %s。%s\n" % (tex_escape(issue["summary"]), location, tex_escape(issue["detail"])))
            if issue.get("evidence_asset"):
                path = issue["evidence_asset"]
                used.add(path)
                lines.append(
                    r"\par\smallskip\noindent\includegraphics"
                    r"[width=.9\linewidth,height=.42\textheight,keepaspectratio]{%s}\par" % path
                )
    if not lines:
        return "", used
    return "\\clearpage\n\\appendix\n\\section{整理与复核说明}\n" + "\n".join(lines), used


def symbol_table(p):
    if not p["symbols"]:
        return ""
    lines = [r"\section*{主要记号}", r"\begingroup\renewcommand{\theHtable}{symbols}",
             r"\begin{longtable}{@{}p{.20\linewidth}p{.49\linewidth}p{.23\linewidth}@{}}",
             r"\toprule 记号 & 含义 & 作用域 \\", r"\midrule\endhead"]
    for s in p["symbols"]:
        lines.append("$%s$ & %s & %s \\\\" % (s["tex"], tex_escape(s["meaning"]), tex_escape(s["scope"])))
    return "\n".join(lines + [r"\bottomrule\end{longtable}", r"\addtocounter{table}{-1}\endgroup"])


def assemble(args):
    root = Path(args.project)
    p, us = project(root), units(root, project(root))
    mode_check(p, args.mode)
    report = validate(root)
    if report["errors"]:
        raise Problem("Structural errors: " + "; ".join(report["errors"]))
    if report["gaps"] and not args.allow_partial:
        raise Problem("Unfinished content; complete it or explicitly use --allow-partial: " + "; ".join(report["gaps"]))
    dest = root / "build" / args.mode
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".assemble-", dir=dest.parent))
    try:
        for template in TEMPLATES.glob("*.tex"):
            shutil.copy2(template, stage / template.name)
        if not (stage / "preamble.tex").exists():
            raise Problem("Missing bundled LaTeX preamble")
        course = inside(root, p["preamble"]).read_text(encoding="utf-8") if p.get("preamble") else ""
        write(stage / "course-preamble.tex", course)
        body = []
        source_map = {"version": 1, "mode": args.mode, "originals_embedded": False,
                      "inputs": [{"id": i["id"], "sha256": i["sha256"]} for i in p["inputs"]],
                      "sources": [{k: v for k, v in src.items() if k in ("id", "input_id", "page", "revision", "transform", "size")} for src in p["sources"]],
                      "units": [], "gap_count": len(report["gaps"])}
        for unit in us:
            text = render_unit(root, unit, args.mode, p.get("presentation", {}).get("source_style", "plain"))
            file_name = "units/%s.tex" % unit["id"]
            write(stage / file_name, text)
            if text:
                body.append("\\input{%s}" % file_name)
            visible = [b for b in unit["blocks"] if not (args.mode == "faithful" and b["origin"] == "explanation")]
            source_map["units"].append({"id": unit["id"], "title": unit["title"], "output_file": file_name,
                "blocks": [{"id": b["id"], "kind": b["kind"], "origin": b["origin"], "refs": b["refs"]} for b in visible]})
        write(stage / "body.tex", "\n".join(body))
        appendix_tex, used_assets = appendix(us, args.mode)
        write(stage / "appendix.tex", appendix_tex)
        write(stage / "symbols.tex", symbol_table(p))
        mode_title = "忠实转录" if args.mode == "faithful" else ("参考资料" if p.get("presentation", {}).get("purpose") == "reference" else "复习讲义")
        style = p.get("presentation", {}).get("source_style", "plain")
        source_label = "浅色块或强调色" if style == "box" else "强调色"
        legend = "" if style == "plain" else "\\noindent{\\small 原材料内容以%s标识；讲解与补充推导使用黑色。}\\par\n" % source_label
        toc = "\\tableofcontents\n\\medskip\n" if len(body) >= 4 else ""
        write(stage / "main.tex", DOCUMENT_CLASS + "\n\\input{preamble.tex}\n\\input{course-preamble.tex}\n"
              "\\begin{document}\n\\EconMakeTitle{%s}{%s}\n%s%s\\input{symbols.tex}\n\\input{body.tex}\n\\input{appendix.tex}\n\\end{document}\n"
              % (tex_escape(p["title"]), mode_title, legend, toc))
        source_map["assets"] = [a for a in p["assets"] if a["path"] in used_assets]
        for asset in source_map["assets"]:
            target = inside(stage, asset["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inside(root, asset["path"]), target)
        save_json(stage / "source-map.json", source_map)
        if dest.exists():
            dest.rename(root / "history" / ("build-" + args.mode + "-" + token()))
        stage.rename(dest)
        data = state(root)
        data["builds"][args.mode] = {"fingerprint": fingerprint(root, p, us, TEMPLATES), "source_digest": source_digest(dest),
                                    "assembled": now(), "compiled": False, "partial": bool(report["gaps"]),
                                    "gaps": report["gaps"], "failed_units": [], "warnings": []}
        save_json(root / "state.json", data)
        return {"directory": str(dest), "mode": args.mode, "partial": bool(report["gaps"]), "gaps": report["gaps"]}, 3 if report["gaps"] else 0
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def context(args, require_pdf=False):
    root = Path(args.project)
    p, data = project(root), state(root)
    us = units(root, p)
    mode_check(p, args.mode)
    report = validate(root)
    if report["errors"]:
        raise Problem("Structural errors: " + "; ".join(report["errors"]))
    b = data["builds"].get(args.mode)
    dest = root / "build" / args.mode
    if not b or b.get("fingerprint") != fingerprint(root, p, us, TEMPLATES):
        raise Problem("Build is absent or stale; assemble the current content first")
    if b.get("source_digest") != source_digest(dest):
        raise Problem("Generated LaTeX/assets changed; edit original fragments and reassemble")
    pdf = dest / "main.pdf"
    if require_pdf and (not b.get("compiled") or not pdf.is_file() or sha_file(pdf) != b.get("pdf_sha256")):
        raise Problem("No current successful PDF; compile first")
    return root, p, us, data, b, dest


def run_process(command, cwd, log, timeout, env=None):
    """Kill the whole TeX/latexmk process group on timeout or interruption."""
    with log.open("wb") as stream:
        proc = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, start_new_session=os.name != "nt", env=env)
        try:
            return proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            if os.name != "nt":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait()
            raise


def latex(dest, source, attempt, timeout):
    attempt.mkdir(parents=True, exist_ok=True)
    console = attempt / "console.log"
    command = ["latexmk", "-norc", "-xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "-no-shell-escape",
               "-outdir=" + str(attempt), source.name]
    try:
        env = os.environ.copy()
        env.update({"openin_any": "p", "openout_any": "p", "TEXMFOUTPUT": str(attempt),
                    "TEXINPUTS": str(dest) + "//:" + str(source.parent) + "//:"})
        code = run_process(command, dest, console, timeout, env=env)
    except subprocess.TimeoutExpired:
        code = 124
    log = attempt / (source.stem + ".log")
    console_text = console.read_text(errors="replace")
    # latexmk's console contains obsolete first-pass warnings; the final .log
    # is authoritative for references and glyphs after all reruns completed.
    text = log.read_text(errors="replace") if log.is_file() else console_text
    errors = list(dict.fromkeys(line.strip() for line in text.splitlines() if line.startswith("!") or re.search(r"\.tex:\d+:", line)))
    warnings = list(dict.fromkeys(line.strip() for line in text.splitlines() if any(k in line for k in ("Warning:", "Overfull", "Missing character:"))))
    pdf = attempt / (source.stem + ".pdf")
    return {"returncode": code, "ok": code == 0 and pdf.is_file() and pdf.stat().st_size > 0,
            "pdf": str(pdf), "log": str(console), "errors": errors[-30:], "warnings": warnings}


def compile_pdf(args):
    if not shutil.which("latexmk") or not shutil.which("xelatex"):
        raise Problem("PDF compilation requires latexmk and xelatex")
    root, p, us, data, b, dest = context(args)
    if not 5 <= args.timeout <= 600:
        raise Problem("Compile timeout must be between 5 and 600 seconds")
    old = dest / "main.pdf"
    if old.exists():
        old.rename(root / "history" / (args.mode + "-" + token() + ".pdf"))
    b.update({"compiled": False, "render": None, "layout_review": None, "pdf_sha256": None})
    save_json(root / "state.json", data)
    attempt = root / "logs" / (args.mode + "-" + token())
    result = latex(dest, dest / "main.tex", attempt, args.timeout)
    if not result["ok"] and args.isolate_failures:
        failed = []
        for unit in us:
            uid = unit["id"]
            if uid in b.get("failed_units", []):
                continue
            probe = attempt / ("probe-" + uid)
            probe.mkdir()
            source = probe / "probe.tex"
            write(source, DOCUMENT_CLASS + "\n\\input{preamble.tex}\n\\input{course-preamble.tex}\n\\begin{document}\n\\input{units/%s.tex}\n\\end{document}\n" % uid)
            outcome = latex(dest, source, probe / "out", args.timeout)
            if not outcome["ok"]:
                failed.append(uid)
        if failed:
            for uid in failed:
                unit = next(u for u in us if u["id"] == uid)
                src = dest / "units" / (uid + ".tex")
                original = dest / "uncompiled" / (uid + ".tex")
                original.parent.mkdir(exist_ok=True)
                shutil.copy2(src, original)
                labels = "\n".join("\\phantomsection\\label{block:%s}" % block["id"] for block in unit["blocks"])
                write(src, heading(unit) + labels + "\n\\EconMissing{本节内容暂未能排版，完整转录源码保留在工程中。}\n")
            b["partial"] = True
            b["failed_units"] = sorted(set(b.get("failed_units", []) + failed))
            mapping = json.loads((dest / "source-map.json").read_text())
            mapping["failed_units"] = b["failed_units"]
            save_json(dest / "source-map.json", mapping)
            b["source_digest"] = source_digest(dest)
            save_json(root / "state.json", data)
            result = latex(dest, dest / "main.tex", attempt / "isolated", args.timeout)
    b["last_attempt"] = result
    b["warnings"] = result["warnings"]
    if result["ok"]:
        shutil.copy2(result["pdf"], dest / "main.pdf")
        from pdf_compat import ensure_unicode_maps
        b["pdf_compat"] = ensure_unicode_maps(dest / "main.pdf")
        b["warnings"].extend("PDF compatibility: " + v for v in b["pdf_compat"]["diagnostics"])
        if b["pdf_compat"]["diagnostics"]:
            b["partial"] = True
        b["compiled"] = now()
        b["pdf_sha256"] = sha_file(dest / "main.pdf")
        b["unresolved_typesetting"] = [w for w in result["warnings"] if "undefined" in w.lower() or "Missing character:" in w]
        if b["unresolved_typesetting"]:
            b["partial"] = True
    save_json(root / "state.json", data)
    return {"mode": args.mode, "compiled": bool(b["compiled"]), "partial": b["partial"], "failed_units": b["failed_units"],
            "pdf": str(dest / "main.pdf") if b["compiled"] else None, "attempt": result}, (3 if b["partial"] else 0) if result["ok"] else 2


def rendering_current(root, b):
    r = b.get("render") or {}
    if not r.get("pages") or r.get("pdf_sha256") != b.get("pdf_sha256"):
        return False
    return all(inside(root, page["path"]).is_file() and sha_file(inside(root, page["path"])) == page["sha256"] for page in r["pages"])


def render(args):
    if not shutil.which("pdftoppm"):
        raise Problem("PDF preview requires pdftoppm")
    if not 72 <= args.dpi <= 300:
        raise Problem("Preview DPI must be 72–300")
    root, p, us, data, b, dest = context(args, require_pdf=True)
    directory = root / "previews" / args.mode
    directory.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".render-", dir=directory.parent))
    try:
        log = root / "logs" / ("render-" + token() + ".log")
        code = run_process(["pdftoppm", "-png", "-r", str(args.dpi), str(dest / "main.pdf"), str(temp / "page")], root, log, 300)
        pages = sorted(temp.glob("page-*.png"), key=lambda f: int(f.stem.split("-")[-1]))
        from pypdf import PdfReader
        if code or len(pages) != len(PdfReader(dest / "main.pdf").pages):
            raise Problem("Incomplete PDF render; see " + str(log))
        if directory.exists():
            directory.rename(root / "history" / ("previews-" + args.mode + "-" + token()))
        temp.rename(directory)
        records = [{"path": (directory / f.name).relative_to(root).as_posix(), "sha256": sha_file(directory / f.name)} for f in pages]
        b["render"] = {"at": now(), "pdf_sha256": b["pdf_sha256"], "pages": records}
        b["layout_review"] = None
        save_json(root / "state.json", data)
        return {"mode": args.mode, "pages": records, "partial": b["partial"]}, 3 if b["partial"] else 0
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def review_layout(args):
    root, p, us, data, b, dest = context(args, require_pdf=True)
    if not rendering_current(root, b):
        raise Problem("Render the current PDF and inspect every page before layout review")
    b["layout_review"] = {"at": now(), "pdf_sha256": b["pdf_sha256"], "render_digest": digest(b["render"]), "note": args.note, "by": "host-agent"}
    save_json(root / "state.json", data)
    return {"mode": args.mode, "layout_review": b["layout_review"]}


def package(args):
    root, p, us, data, b, dest = context(args, require_pdf=True)
    content_reviewed = all(data["reviews"].get(u["id"], {}).get("digest") == unit_digest(root, p, u) for u in us)
    lr = b.get("layout_review") or {}
    layout_reviewed = (rendering_current(root, b) and lr.get("pdf_sha256") == b["pdf_sha256"] and lr.get("render_digest") == digest(b["render"]))
    reviewed = content_reviewed and layout_reviewed
    if not reviewed and not args.allow_unreviewed:
        raise Problem("Content/layout review is missing or stale; inspect first, or explicitly use --allow-unreviewed")
    status = "partial" if b["partial"] else ("reviewed" if reviewed else "unreviewed")
    delivery = {"status": status, "mode": args.mode, "content_reviewed": content_reviewed, "layout_reviewed": layout_reviewed,
                "failed_units": b["failed_units"], "gap_count": len(b["gaps"]), "typesetting_warning_count": len(b["warnings"]), "pdf_sha256": b["pdf_sha256"]}
    description = ("# 交付说明\n\n状态：%s。\n\n本工程使用 XeLaTeX / latexmk，运行 `latexmk -norc -xelatex -no-shell-escape main.tex` 编译。"
                   "\n重编译后运行 `python3 pdf_compat.py main.pdf` 内嵌中文 Unicode 映射（需要 pypdf 和 TeX adobemapping）。已交付的 PDF 已完成此处理。\n\n正文在 units/，附录局部截图在 assets/，来源记录见 source-map.json；完整原始材料未嵌入。"
                   "失败单元如有，源码保留在 uncompiled/。\n\n内容复核：%s；页面复核：%s。详细状态见 delivery.json。\n" %
                   (status, content_reviewed, layout_reviewed))
    out = root / "output"
    out.mkdir(exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".package-", suffix=".zip", dir=out)
    os.close(fd)
    temp = Path(name)
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as archive:
            for f in sorted(dest.rglob("*")):
                rel = f.relative_to(dest).as_posix()
                if f.is_file() and (f.suffix == ".tex" or rel.startswith("assets/") or rel in ("main.pdf", "source-map.json")):
                    archive.write(f, rel)
            archive.write(Path(__file__).with_name("pdf_compat.py"), "pdf_compat.py")
            archive.write(Path(__file__).resolve().parent.parent / "LICENSE", "LICENSE")
            archive.writestr("DELIVERY.md", description)
            archive.writestr("delivery.json", json.dumps(delivery, ensure_ascii=False, indent=2))
        os.replace(temp, out / (args.mode + ".zip"))
        pdf_temp = out / ("." + token() + ".pdf")
        shutil.copy2(dest / "main.pdf", pdf_temp)
        os.replace(pdf_temp, out / (args.mode + ".pdf"))
        save_json(out / (args.mode + "-delivery.json"), delivery)
    finally:
        temp.unlink(missing_ok=True)
    return {"pdf": str(out / (args.mode + ".pdf")), "project_zip": str(out / (args.mode + ".zip")), **delivery}, 3 if status != "reviewed" else 0
