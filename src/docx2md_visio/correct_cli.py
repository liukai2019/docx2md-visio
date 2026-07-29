from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .correction import apply_safe_fixes, audit_markdown, write_correction_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docx2md-visio-correct",
        description="Audit Markdown and optionally apply semantics-preserving fixes.",
    )
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--reference", type=Path, help="Optional MarkItDown/other conversion.")
    parser.add_argument("--write", action="store_true", help="Apply safe fixes in place.")
    parser.add_argument("--report-dir", type=Path, help="Report directory (default: beside Markdown).")
    parser.add_argument(
        "--fail-on",
        choices=["never", "error", "warning", "review"],
        default="error",
        help="Return 2 when this severity or a higher one is found.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.markdown.is_file():
        print(f"error: Markdown does not exist: {args.markdown}", file=sys.stderr)
        return 1
    text = args.markdown.read_text(encoding="utf-8")
    reference_text = (
        args.reference.read_text(encoding="utf-8")
        if args.reference and args.reference.is_file()
        else None
    )
    if args.reference and reference_text is None:
        print(f"error: Reference does not exist: {args.reference}", file=sys.stderr)
        return 1
    result = audit_markdown(text, args.markdown, reference_text, args.reference)
    if args.write:
        args.markdown.write_text(apply_safe_fixes(text), encoding="utf-8")
    report_dir = args.report_dir or args.markdown.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    write_correction_reports(
        result,
        report_dir / "correction-report.json",
        report_dir / "correction-report.md",
    )
    print(f"Audited {args.markdown}; {len(result.findings)} finding(s).")
    if args.fail_on == "never":
        return 0
    ranks = {"info": 0, "review": 1, "warning": 2, "error": 3}
    threshold = {"review": 1, "warning": 2, "error": 3}[args.fail_on]
    return 2 if any(ranks[item.severity] >= threshold for item in result.findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
