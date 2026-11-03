#!/usr/bin/env python3
"""Host-agent utility CLI; recognition remains with the host model."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from core import Problem, locked
import media
import model


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Report available local dependencies")
    init = commands.add_parser("init", help="Create a project from ordered files or directories")
    init.add_argument("--project", required=True)
    init.add_argument("--inputs", nargs="+", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--mode", required=True, choices=["faithful", "study", "both"])
    init.add_argument("--purpose", choices=["revision", "reference"], default="revision")
    init.add_argument("--source-style", choices=["plain", "accent", "box"], default="plain")
    init.add_argument("--domains", nargs="+", default=[], choices=["macro", "micro", "econometrics", "math"])
    prep = commands.add_parser("prepare", help="Prepare full images and overlapping tiles")
    prep.add_argument("--project", required=True)
    prep.add_argument("--source")
    prep.add_argument("--dpi", type=int, default=300)
    prep.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0)
    prep.add_argument("--quad", type=float, nargs=8, metavar="COORD")
    prep.add_argument("--enhance", action="store_true")
    prep.add_argument("--tile-size", type=int, default=1600)
    prep.add_argument("--overlap", type=float, default=0.15)
    crop = commands.add_parser("crop", help="Save an attributed source region")
    crop.add_argument("--project", required=True)
    crop.add_argument("--source", required=True)
    crop.add_argument("--box", type=float, nargs=4, required=True)
    crop.add_argument("--name", required=True)
    unit = commands.add_parser("unit", help="Add a logical unit without overwriting existing work")
    unit.add_argument("--project", required=True)
    unit.add_argument("--id", required=True)
    unit.add_argument("--title", required=True)
    unit.add_argument("--sources", nargs="+", required=True)
    for name in ("validate", "status"):
        commands.add_parser(name).add_argument("--project", required=True)
    review = commands.add_parser("review", help="Record a host review after actually inspecting the material")
    review.add_argument("--project", required=True)
    review.add_argument("--kind", choices=["content", "layout"], required=True)
    review.add_argument("--unit")
    review.add_argument("--mode", choices=["faithful", "study"])
    review.add_argument("--note", required=True)
    for name in ("assemble", "compile", "render", "package"):
        command = commands.add_parser(name)
        command.add_argument("--project", required=True)
        command.add_argument("--mode", choices=["faithful", "study"], required=True)
        if name == "assemble":
            command.add_argument("--allow-partial", action="store_true")
        elif name == "compile":
            command.add_argument("--isolate-failures", action="store_true")
            command.add_argument("--timeout", type=int, default=120)
        elif name == "render":
            command.add_argument("--dpi", type=int, default=130)
        elif name == "package":
            command.add_argument("--allow-unreviewed", action="store_true")
    return p


def dispatch(args):
    if args.command == "doctor":
        data = media.doctor()
        return data, 2 if data["required_missing"] else 0
    if args.command == "init":
        return media.initialize(args), 0
    root = Path(args.project).expanduser().resolve()
    if not (root / "project.json").is_file():
        raise Problem("Project does not exist: " + str(root))
    args.project = str(root)
    if args.command == "validate":
        data = model.validate(root)
        return data, 2 if data["errors"] else (3 if data["gaps"] else 0)
    if args.command == "status":
        return model.status(root), 0
    with locked(root):
        if args.command == "prepare":
            return media.prepare(args), 0
        if args.command == "crop":
            return media.crop(args), 0
        if args.command == "unit":
            return media.add_unit(args), 0
        if args.command == "review":
            if not args.note.strip():
                raise Problem("Review note must describe what was inspected")
            if args.kind == "content":
                if not args.unit:
                    raise Problem("Content review requires --unit")
                return model.review_content(args), 0
            if not args.mode:
                raise Problem("Layout review requires --mode")
            from build import review_layout
            return review_layout(args), 0
        if args.command in ("assemble", "compile", "render", "package"):
            import build
            command = {"assemble": build.assemble, "compile": build.compile_pdf, "render": build.render, "package": build.package}[args.command]
            return command(args)
    raise Problem("Unknown command")


def main():
    args = parser().parse_args()
    try:
        data, code = dispatch(args)
    except (Problem, OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as exc:
        data, code = {"error": str(exc), "command": args.command}, 2
    except KeyboardInterrupt:
        data, code = {"error": "Interrupted; existing project data is retained", "command": args.command}, 2
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
