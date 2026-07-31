from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .corrections import (
    CorrectionError,
    backup_final_mmds,
    default_corrections_dir,
    message_conservation,
    restore_final_mmd,
)


def _manifest(output_dir: Path) -> dict:
    return json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))


def _diagram(output_dir: Path, diagram_id: str) -> tuple[dict, Path]:
    manifest = _manifest(output_dir)
    matches = [
        item for item in manifest.get("diagrams", []) if item.get("id") == diagram_id
    ]
    if len(matches) != 1 or not matches[0].get("source_vsdx"):
        raise CorrectionError(f"Cannot resolve {diagram_id} from manifest.")
    record = matches[0]
    return record, output_dir / Path(record["source_vsdx"]).parent


def _scaffold(output_dir: Path, diagram_id: str, kind: str) -> Path:
    record, directory = _diagram(output_dir, diagram_id)
    destination = directory / "final.mmd"
    if destination.exists():
        raise CorrectionError(
            f"{destination} already exists; back it up before replacing it."
        )
    if kind == "raw":
        raw = output_dir / record.get("raw_mermaid", "")
        if not raw.is_file():
            raise CorrectionError(f"Missing raw Mermaid for {diagram_id}.")
        source = raw.read_text(encoding="utf-8")
    elif kind == "sequence":
        source = (
            "sequenceDiagram\n"
            "    %% TODO: define participants, then copy every verified message\n"
            "    %% from geometry-summary.md in top-to-bottom order.\n"
        )
    else:
        source = (
            "flowchart TD\n"
            "    %% TODO: define nodes, edges, and meaningful visual groups.\n"
        )
    destination.write_text(source, encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docx2md-visio-review",
        description="Manage human Mermaid review and durable correction assets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("list", "backup"):
        command = subparsers.add_parser(name)
        command.add_argument("output_dir", type=Path)
        if name == "backup":
            command.add_argument("--corrections-dir", type=Path)
    scaffold = subparsers.add_parser("scaffold")
    scaffold.add_argument("output_dir", type=Path)
    scaffold.add_argument("--diagram", required=True)
    scaffold.add_argument("--type", choices=["sequence", "flowchart", "raw"], required=True)
    check = subparsers.add_parser("check")
    check.add_argument("output_dir", type=Path)
    check.add_argument("--diagram", required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("output_dir", type=Path)
    restore.add_argument("--diagram", required=True)
    restore.add_argument("--corrections-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        output_dir = args.output_dir.resolve()
        if args.command == "list":
            manifest = _manifest(output_dir)
            for item in manifest.get("diagrams", []):
                source = item.get("source_vsdx")
                final = (
                    output_dir / Path(source).parent / "final.mmd"
                    if source
                    else None
                )
                print(
                    f"{item.get('id')}: status={item.get('status')}; "
                    f"final={'yes' if final and final.is_file() else 'no'}"
                )
        elif args.command == "backup":
            records = backup_final_mmds(
                output_dir, args.corrections_dir
            )
            root = args.corrections_dir or default_corrections_dir(output_dir)
            print(f"Backed up {len(records)} final.mmd file(s) under {root}.")
        elif args.command == "scaffold":
            print(_scaffold(output_dir, args.diagram, args.type))
        elif args.command == "check":
            record, directory = _diagram(output_dir, args.diagram)
            geometry = output_dir / record.get("geometry_json", "")
            final = directory / "final.mmd"
            if not geometry.is_file() or not final.is_file():
                raise CorrectionError("diagram.json or final.mmd is missing.")
            result = message_conservation(geometry, final)
            (directory / "manual-check.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result["passed"]:
                return 2
        elif args.command == "restore":
            print(
                restore_final_mmd(
                    output_dir, args.diagram, args.corrections_dir
                )
            )
    except (CorrectionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
