from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import PipelineError, convert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docx2md-visio",
        description="Convert DOCX documents with embedded VSDX diagrams to Markdown.",
    )
    parser.add_argument("input", type=Path, help="Input .docx file")
    parser.add_argument(
        "-o", "--output-dir", type=Path, required=True, help="Output directory"
    )
    parser.add_argument(
        "--pandoc", default="pandoc", help="Pandoc executable path (default: pandoc)"
    )
    parser.add_argument(
        "--converter",
        action="append",
        dest="converter_command",
        metavar="ARG",
        help=(
            "One convert2mermaid command token; repeat for command prefixes. "
            "Example: --converter node --converter tools/convert2mermaid/dist/cli.js"
        ),
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="Keep unpacked DOCX and draft Markdown under the output directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = convert(
            args.input,
            args.output_dir,
            pandoc=args.pandoc,
            converter_command=args.converter_command,
            keep_work=args.keep_work,
        )
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    converted = sum(d.status == "converted" for d in manifest.diagrams)
    print(
        f"Wrote {manifest.output_markdown}; "
        f"converted {converted}/{len(manifest.diagrams)} Visio diagrams."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

