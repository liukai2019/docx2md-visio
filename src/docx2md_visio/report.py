from __future__ import annotations

import json
from pathlib import Path

from .models import Manifest


def write_manifest(manifest: Manifest, path: Path) -> None:
    path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_report(manifest: Manifest, path: Path) -> None:
    converted = sum(d.status == "converted" for d in manifest.diagrams)
    lines = [
        "# Conversion report",
        "",
        f"- Source: `{manifest.source_document}`",
        f"- Markdown: `{manifest.output_markdown}`",
        f"- Diagrams found: {len(manifest.diagrams)}",
        f"- Diagrams converted: {converted}",
        f"- Diagrams unresolved: {len(manifest.diagrams) - converted}",
        "",
        "## Diagrams",
        "",
        "| ID | Paragraph | Preview | Embedded Visio | Status |",
        "|---|---:|---|---|---|",
    ]
    for diagram in manifest.diagrams:
        lines.append(
            "| {id} | {paragraph} | `{preview}` | `{embedding}` | {status} |".format(
                id=diagram.id,
                paragraph=diagram.paragraph_index
                if diagram.paragraph_index is not None
                else "—",
                preview=diagram.preview_part or "—",
                embedding=diagram.embedding_part or "—",
                status=diagram.status,
            )
        )
        for warning in diagram.warnings:
            lines.append(f"\n> **{diagram.id}:** {warning}")
    if manifest.warnings:
        lines.extend(["", "## Pipeline warnings", ""])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

