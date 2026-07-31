from __future__ import annotations

from pathlib import Path

from .models import Manifest


def write_human_review_guide(manifest: Manifest, output_dir: Path) -> Path:
    pending = [
        diagram
        for diagram in manifest.diagrams
        if diagram.status == "review_required"
    ]
    lines = [
        "# Human Mermaid review",
        "",
        "The original preview is authoritative until a human approves `final.mmd`.",
        "Claude should remind and validate; it must not redraw a complex diagram",
        "unless the human explicitly asks for a small, bounded edit.",
        "",
        "## Before editing or rerunning conversion",
        "",
        "Back up every existing `final.mmd` outside the output directory:",
        "",
        "```powershell",
        f"docx2md-visio-review backup {output_dir}",
        "```",
        "",
        "The default durable asset store is the sibling `corrections/` directory.",
        "Each `.mmd` has an adjacent `.metadata.json` provenance record.",
        "",
        "## Review queue",
        "",
        "| Diagram | Status | Geometry summary | Final asset |",
        "|---|---|---|---|",
    ]
    for diagram in manifest.diagrams:
        final = (
            Path(diagram.source_vsdx).parent / "final.mmd"
            if diagram.source_vsdx
            else None
        )
        lines.append(
            f"| `{diagram.id}` | {diagram.status} | "
            f"`{diagram.geometry_summary or '—'}` | `{final.as_posix() if final else '—'}` |"
        )
    lines.extend(
        [
            "",
            "## Process one diagram",
            "",
            "1. Compare the original Word/Visio preview with `geometry-summary.md`,",
            "   `diagnostic.svg`, and `raw.mmd`.",
            "2. Choose exactly one outcome:",
            "   - **keep original**: do nothing; the preview remains in Markdown;",
            "   - **accept draft**: scaffold from `raw.mmd`, inspect every item;",
            "   - **manual redraw**: scaffold a blank sequence or flowchart.",
            "3. Edit `final.mmd` yourself with a local Mermaid preview.",
            "4. Run the deterministic message-conservation check.",
            "5. Fix or consciously explain every missing/unexpected message.",
            "6. Apply only after visual comparison with the original.",
            "",
            "Accept an existing draft:",
            "",
            "```powershell",
            f"docx2md-visio-review scaffold {output_dir} --diagram DIAGRAM-ID --type raw",
            "```",
            "",
            "Start a manual sequence redraw:",
            "",
            "```powershell",
            f"docx2md-visio-review scaffold {output_dir} --diagram DIAGRAM-ID --type sequence",
            "```",
            "",
            "Check content conservation:",
            "",
            "```powershell",
            f"docx2md-visio-review check {output_dir} --diagram DIAGRAM-ID",
            "```",
            "",
            "Apply and automatically back up all `final.mmd` files:",
            "",
            "```powershell",
            f"docx2md-visio-apply {output_dir} --diagram DIAGRAM-ID --approve",
            "```",
            "",
            "If message differences are intentional and have been checked manually:",
            "",
            "```powershell",
            f"docx2md-visio-apply {output_dir} --diagram DIAGRAM-ID --approve --allow-message-differences",
            "```",
            "",
            "## Restore a previous approved asset",
            "",
            "Restoration matches the current source VSDX SHA-256; it never applies",
            "the correction automatically:",
            "",
            "```powershell",
            f"docx2md-visio-review restore {output_dir} --diagram DIAGRAM-ID",
            "```",
            "",
            f"Pending human-review diagrams: {len(pending)}.",
        ]
    )
    path = output_dir / "HUMAN-REVIEW.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

