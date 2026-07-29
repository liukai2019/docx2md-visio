from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .markdown import merge_markdown
from .models import Diagram, Manifest
from .report import write_report

ALLOWED_STARTS = (
    "flowchart ",
    "graph ",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "gantt",
    "pie",
    "mindmap",
    "timeline",
    "journey",
    "quadrantChart",
    "requirementDiagram",
    "gitGraph",
    "packet",
    "architecture",
    "block-beta",
)


class ApplyError(RuntimeError):
    pass


def _validate_mermaid(source: str) -> None:
    stripped = source.strip()
    if not stripped:
        raise ApplyError("final.mmd is empty.")
    if "```" in stripped:
        raise ApplyError("final.mmd must not contain Markdown code fences.")
    first_line = stripped.splitlines()[0].strip()
    if not first_line.startswith(ALLOWED_STARTS):
        raise ApplyError(f"Unsupported Mermaid declaration: {first_line}")


def apply_review(output_dir: Path, diagram_id: str, approve: bool) -> Path:
    if not approve:
        raise ApplyError("Refusing to modify Markdown without --approve.")
    output_dir = output_dir.resolve()
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ApplyError(f"Missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = [
        record
        for record in manifest.get("diagrams", [])
        if record.get("id") == diagram_id
    ]
    if len(records) != 1:
        raise ApplyError(f"Manifest does not contain exactly one {diagram_id}.")
    record = records[0]
    source_vsdx = record.get("source_vsdx")
    if not source_vsdx:
        raise ApplyError(f"{diagram_id} has no extracted source VSDX.")
    diagram_dir = output_dir / Path(source_vsdx).parent
    final_path = diagram_dir / "final.mmd"
    if not final_path.is_file():
        raise ApplyError(f"Missing reviewed Mermaid: {final_path}")
    final_source = final_path.read_text(encoding="utf-8-sig")
    _validate_mermaid(final_source)

    markdown_path = output_dir / manifest["output_markdown"]
    if not markdown_path.is_file():
        raise ApplyError(f"Missing output Markdown: {markdown_path}")
    backup = markdown_path.with_suffix(markdown_path.suffix + ".pre-review")
    if not backup.exists():
        shutil.copy2(markdown_path, backup)

    record["raw_mermaid"] = final_path.relative_to(output_dir).as_posix()
    diagram = Diagram(**{
        key: value
        for key, value in record.items()
        if key in Diagram.__dataclass_fields__
    })
    diagram.status = "mermaid_generated"
    before = markdown_path.read_text(encoding="utf-8")
    after = merge_markdown(before, [diagram], output_dir)
    if after == before or diagram.status != "converted":
        raise ApplyError(
            f"Could not replace the preview for {diagram_id} unambiguously."
        )
    markdown_path.write_text(after, encoding="utf-8")
    record["status"] = "converted_after_review"
    record["final_mermaid"] = final_path.relative_to(output_dir).as_posix()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_manifest = Manifest(
        source_document=manifest.get("source_document", ""),
        output_markdown=manifest["output_markdown"],
        diagrams=[
            Diagram(
                **{
                    key: value
                    for key, value in item.items()
                    if key in Diagram.__dataclass_fields__
                }
            )
            for item in manifest.get("diagrams", [])
        ],
        warnings=manifest.get("warnings", []),
        tool_versions=manifest.get("tool_versions", {}),
    )
    write_report(report_manifest, output_dir / "conversion-report.md")
    return markdown_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply one human-approved final.mmd to converted Markdown."
    )
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--diagram", required=True)
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args(argv)
    try:
        path = apply_review(args.output_dir, args.diagram, args.approve)
    except (ApplyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Applied {args.diagram} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
