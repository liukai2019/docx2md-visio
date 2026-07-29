from __future__ import annotations

from pathlib import Path

from docx2md_visio.markdown import merge_markdown
from docx2md_visio.models import Diagram


def test_merge_replaces_exact_preview_and_preserves_source_link(
    tmp_path: Path,
) -> None:
    diagram_dir = tmp_path / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    (diagram_dir / "raw.mmd").write_text(
        'flowchart LR\n  A["Start"] --> B["End"]\n', encoding="utf-8"
    )
    diagram = Diagram(
        id="diagram-001",
        document_part="word/document.xml",
        document_order=0,
        paragraph_index=1,
        preview_part="word/media/image1.png",
        embedding_part="word/embeddings/diagram.vsdx",
        source_vsdx="assets/visio/diagram-001/source.vsdx",
        raw_mermaid="assets/visio/diagram-001/raw.mmd",
    )

    result = merge_markdown(
        "Before\n\n![diagram](assets/media/image1.png)\n\nAfter\n",
        [diagram],
        tmp_path,
    )

    assert "![diagram]" not in result
    assert "```mermaid" in result
    assert 'A["Start"] --> B["End"]' in result
    assert "[Original Visio diagram](assets/visio/diagram-001/source.vsdx)" in result
    assert diagram.status == "converted"


def test_merge_does_not_guess_when_preview_is_duplicated(tmp_path: Path) -> None:
    diagram = Diagram(
        id="diagram-001",
        document_part="word/document.xml",
        document_order=0,
        paragraph_index=1,
        preview_part="word/media/image1.png",
        embedding_part="word/embeddings/diagram.vsdx",
        raw_mermaid="assets/visio/diagram-001/raw.mmd",
    )
    markdown = "![](assets/media/image1.png)\n\n![](assets/media/image1.png)\n"

    result = merge_markdown(markdown, [diagram], tmp_path)

    assert result == markdown
    assert diagram.status == "unresolved"
    assert any("multiple times" in warning for warning in diagram.warnings)


def test_merge_replaces_complete_multiline_html_img_tag(tmp_path: Path) -> None:
    diagram_dir = tmp_path / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    (diagram_dir / "raw.mmd").write_text(
        'flowchart LR\n  A["Start"] --> B["End"]\n', encoding="utf-8"
    )
    diagram = Diagram(
        id="diagram-001",
        document_part="word/document.xml",
        document_order=0,
        paragraph_index=1,
        preview_part="word/media/image1.emf",
        embedding_part="word/embeddings/diagram.vsdx",
        source_vsdx="assets/visio/diagram-001/source.vsdx",
        raw_mermaid="assets/visio/diagram-001/raw.mmd",
    )
    markdown = (
        "Before\n\n"
        '<img src="assets/media/image1.emf"\n'
        'style="width:6.5in;height:3.2in" alt="Visio diagram" />\n\n'
        "图 2 Example\n\nAfter\n"
    )

    result = merge_markdown(markdown, [diagram], tmp_path)

    assert "<img" not in result
    assert "/>" not in result
    assert "style=" not in result
    assert "```mermaid" in result
    assert "图 2 Example" in result
    assert diagram.status == "converted"


def test_merge_supports_single_quoted_and_unquoted_html_src(
    tmp_path: Path,
) -> None:
    for html in (
        "<IMG ALT='x' SRC='assets/media/image1.png'/>",
        "<img src=assets/media/image1.png class=x>",
    ):
        diagram_dir = tmp_path / "assets/visio/diagram-001"
        diagram_dir.mkdir(parents=True, exist_ok=True)
        (diagram_dir / "raw.mmd").write_text(
            "flowchart LR\n  A --> B\n", encoding="utf-8"
        )
        diagram = Diagram(
            id="diagram-001",
            document_part="word/document.xml",
            document_order=0,
            paragraph_index=1,
            preview_part="word/media/image1.png",
            embedding_part="word/embeddings/diagram.vsdx",
            source_vsdx="assets/visio/diagram-001/source.vsdx",
            raw_mermaid="assets/visio/diagram-001/raw.mmd",
        )

        result = merge_markdown(html, [diagram], tmp_path)

        assert "<img" not in result.lower()
        assert "```mermaid" in result
        assert diagram.status == "converted"
