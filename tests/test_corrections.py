from __future__ import annotations

import json
from pathlib import Path

from docx2md_visio.corrections import (
    backup_final_mmds,
    message_conservation,
    restore_final_mmd,
)


def _output(tmp_path: Path) -> Path:
    output = tmp_path / "output"
    diagram_dir = output / "assets/visio/diagram-001"
    diagram_dir.mkdir(parents=True)
    source_doc = tmp_path / "input.docx"
    source_doc.write_bytes(b"document")
    (diagram_dir / "source.vsdx").write_bytes(b"source-v1")
    (diagram_dir / "final.mmd").write_text(
        "sequenceDiagram\nA->>B: INVITE F1\nB-->>A: 100 Trying F2\n",
        encoding="utf-8",
    )
    geometry = {
        "pages": [
            {
                "shapes": [
                    {"kind": "one_dimensional", "text": "INVITE F1"},
                    {"kind": "one_dimensional", "text": "100 Trying F2"},
                ]
            }
        ]
    }
    (diagram_dir / "diagram.json").write_text(
        json.dumps(geometry), encoding="utf-8"
    )
    manifest = {
        "source_document": str(source_doc),
        "output_markdown": "input.md",
        "diagrams": [
            {
                "id": "diagram-001",
                "document_part": "word/document.xml",
                "document_order": 0,
                "paragraph_index": 7,
                "preview_part": "word/media/image1.emf",
                "embedding_part": "word/embeddings/Microsoft_Visio_1.vsdx",
                "source_vsdx": "assets/visio/diagram-001/source.vsdx",
                "geometry_json": "assets/visio/diagram-001/diagram.json",
            }
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return output


def test_backup_has_adjacent_self_contained_provenance(tmp_path: Path) -> None:
    output = _output(tmp_path)
    corrections = tmp_path / "durable-corrections"

    records = backup_final_mmds(
        output, corrections, approved_diagram="diagram-001"
    )

    record = records[0]
    asset = corrections / record["asset"]
    metadata_path = corrections / record["metadata"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert asset.is_file()
    assert metadata_path.parent == asset.parent
    assert metadata["source"]["document_name"] == "input.docx"
    assert metadata["source"]["document_sha256"]
    assert metadata["source"]["diagram_id"] == "diagram-001"
    assert metadata["source"]["paragraph_index"] == 7
    assert metadata["source"]["embedding_part"].endswith(".vsdx")
    assert metadata["source"]["source_vsdx_sha256"]
    assert metadata["source"]["geometry_json_sha256"]
    assert metadata["backup_events"][0]["approved"] is True


def test_restore_matches_source_vsdx_hash(tmp_path: Path) -> None:
    output = _output(tmp_path)
    corrections = tmp_path / "corrections"
    original = (
        output / "assets/visio/diagram-001/final.mmd"
    ).read_text(encoding="utf-8")
    backup_final_mmds(output, corrections, approved_diagram="diagram-001")
    (output / "assets/visio/diagram-001/final.mmd").unlink()

    restored = restore_final_mmd(output, "diagram-001", corrections)

    assert restored.read_text(encoding="utf-8") == original


def test_backup_preserves_every_final_mmd(tmp_path: Path) -> None:
    output = _output(tmp_path)
    second = output / "assets/visio/diagram-002"
    second.mkdir(parents=True)
    (second / "source.vsdx").write_bytes(b"source-v2")
    (second / "final.mmd").write_text(
        "flowchart TD\nA --> B\n", encoding="utf-8"
    )
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["diagrams"].append(
        {
            "id": "diagram-002",
            "source_vsdx": "assets/visio/diagram-002/source.vsdx",
            "embedding_part": "word/embeddings/Microsoft_Visio_2.vsdx",
        }
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    records = backup_final_mmds(output, tmp_path / "corrections")

    assert {record["diagram_id"] for record in records} == {
        "diagram-001",
        "diagram-002",
    }
    for record in records:
        assert (tmp_path / "corrections" / record["asset"]).is_file()
        assert (tmp_path / "corrections" / record["metadata"]).is_file()


def test_message_conservation_reports_missing_and_unexpected(tmp_path: Path) -> None:
    output = _output(tmp_path)
    diagram_dir = output / "assets/visio/diagram-001"
    final = diagram_dir / "final.mmd"
    final.write_text(
        "sequenceDiagram\nA->>B: INVITE F1\nB-->>A: EXTRA\n",
        encoding="utf-8",
    )

    result = message_conservation(diagram_dir / "diagram.json", final)

    assert result["missing"] == ["100 Trying F2"]
    assert result["unexpected"] == ["EXTRA"]
    assert not result["passed"]
