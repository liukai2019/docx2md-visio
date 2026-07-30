from __future__ import annotations

from pathlib import Path
import zipfile

from docx2md_visio.docx import extract_visio_files, inspect_document, safe_extract_docx

from .helpers import make_docx


def test_inspect_maps_preview_embedding_and_paragraph(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    package = tmp_path / "package"
    make_docx(source)
    safe_extract_docx(source, package)

    diagrams = inspect_document(package)

    assert len(diagrams) == 1
    assert diagrams[0].paragraph_index == 1
    assert diagrams[0].preview_part == "word/media/image1.png"
    assert diagrams[0].embedding_part == (
        "word/embeddings/Microsoft_Visio_1.vsdx"
    )


def test_extract_copies_vsdx_without_modifying_package(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    package = tmp_path / "package"
    output = tmp_path / "output"
    make_docx(source)
    safe_extract_docx(source, package)
    diagrams = inspect_document(package)

    extract_visio_files(package, diagrams, output)

    extracted = output / "assets/visio/diagram-001/source.vsdx"
    with zipfile.ZipFile(source) as archive:
        original = archive.read("word/embeddings/Microsoft_Visio_1.vsdx")
    assert extracted.read_bytes() == original
    assert diagrams[0].source_vsdx == "assets/visio/diagram-001/source.vsdx"
