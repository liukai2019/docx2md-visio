from __future__ import annotations

import json
from pathlib import Path

import pytest

from docx2md_visio.apply_review import ApplyError, apply_review
from docx2md_visio.context import write_review_inputs
from docx2md_visio.markdown import map_markdown_images
from docx2md_visio.models import Diagram


def _diagram() -> Diagram:
    return Diagram(
        id="diagram-001",
        document_part="word/document.xml",
        document_order=0,
        paragraph_index=3,
        preview_part="word/media/image1.emf",
        embedding_part="word/embeddings/diagram.vsdx",
        source_vsdx="assets/visio/diagram-001/source.vsdx",
        raw_mermaid="assets/visio/diagram-001/raw.mmd",
        status="review_required",
    )


def test_context_uses_nearest_heading_and_surrounding_text(
    tmp_path: Path,
) -> None:
    diagram = _diagram()
    diagram_dir = tmp_path / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    markdown = (
        "# Earlier\n\nOld text.\n\n"
        "## Call flow\n\nBefore the diagram.\n\n"
        '<img src="assets/media/image1.emf" style="width:5in" />\n\n'
        "Figure 2 signaling.\n\nAfter the diagram.\n\n"
        "## Next section\n\nNot part of this context.\n"
    )
    map_markdown_images(markdown, [diagram])

    write_review_inputs(markdown, [diagram], tmp_path)

    context = (diagram_dir / "context.md").read_text(encoding="utf-8")
    prompt = (diagram_dir / "review-prompt.md").read_text(encoding="utf-8")
    assert "Nearest heading: Call flow" in context
    assert "Before the diagram." in context
    assert "Figure 2 signaling." in context
    assert "Not part of this context." not in context
    assert "do not include triple-backtick fences" in prompt


def test_apply_review_replaces_preview_and_creates_backup(
    tmp_path: Path,
) -> None:
    diagram = _diagram()
    diagram_dir = tmp_path / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    (diagram_dir / "source.vsdx").write_bytes(b"source")
    (diagram_dir / "raw.mmd").write_text("flowchart TD\n", encoding="utf-8")
    (diagram_dir / "final.mmd").write_text(
        "sequenceDiagram\n"
        "    participant A\n"
        "    participant B\n"
        "    A->>B: INVITE\n",
        encoding="utf-8",
    )
    markdown_path = tmp_path / "document.md"
    original = '<img src="assets/media/image1.emf" />\n'
    markdown_path.write_text(original, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "source_document": "input.docx",
        "output_markdown": "document.md",
        "diagrams": [diagram.to_dict()],
        "warnings": [],
        "tool_versions": {},
    }
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    result = apply_review(tmp_path, "diagram-001", approve=True)

    rendered = result.read_text(encoding="utf-8")
    saved_manifest = json.loads(
        (tmp_path / "manifest.json").read_text(encoding="utf-8")
    )
    assert "```mermaid\nsequenceDiagram" in rendered
    assert "A->>B: INVITE" in rendered
    assert "<img" not in rendered
    assert markdown_path.with_suffix(".md.pre-review").read_text(
        encoding="utf-8"
    ) == original
    assert saved_manifest["diagrams"][0]["status"] == "converted_after_review"
    report = (tmp_path / "conversion-report.md").read_text(encoding="utf-8")
    assert "Diagrams converted: 1" in report
    assert "converted_after_review" in report


def test_apply_review_requires_explicit_approval(tmp_path: Path) -> None:
    with pytest.raises(ApplyError, match="--approve"):
        apply_review(tmp_path, "diagram-001", approve=False)


def test_apply_review_rejects_fenced_mermaid(tmp_path: Path) -> None:
    diagram = _diagram()
    diagram_dir = tmp_path / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    (diagram_dir / "source.vsdx").write_bytes(b"source")
    (diagram_dir / "final.mmd").write_text(
        "```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8"
    )
    (tmp_path / "document.md").write_text(
        '<img src="assets/media/image1.emf" />', encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "output_markdown": "document.md",
                "diagrams": [diagram.to_dict()],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ApplyError, match="code fences"):
        apply_review(tmp_path, "diagram-001", approve=True)
