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
        "--converter-mode",
        choices=["native", "auto"],
        default="native",
        help=(
            "Use the built-in parser only (native, default), or try "
            "convert2mermaid and cross-check it (auto)."
        ),
    )
    parser.add_argument(
        "--review-policy",
        choices=["all", "complex"],
        default="all",
        help=(
            "Preserve every original preview for human review (all, default), "
            "or auto-replace only basic low-risk diagrams (complex)."
        ),
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="Keep unpacked DOCX and draft Markdown under the output directory",
    )
    parser.add_argument(
        "--markitdown",
        action="append",
        dest="markitdown_command",
        metavar="ARG",
        help=(
            "Optional MarkItDown command token; repeat for prefixes such as "
            "--markitdown python --markitdown -m --markitdown markitdown."
        ),
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
            converter_mode=args.converter_mode,
            review_policy=args.review_policy,
            markitdown_command=args.markitdown_command,
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
