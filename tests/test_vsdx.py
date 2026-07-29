from __future__ import annotations

import runpy
from pathlib import Path

from docx2md_visio.vsdx import (
    assess_vsdx,
    convert_vsdx,
    mermaid_structure_counts,
    parse_vsdx,
)


def _generator_module() -> dict:
    return runpy.run_path(
        str(Path(__file__).parents[1] / "scripts" / "generate_sample.py"),
        run_name="sample_generator",
    )


def test_native_parser_handles_mixed_and_empty_visio_text(tmp_path: Path) -> None:
    sample = tmp_path / "sample.vsdx"
    _generator_module()["write_vsdx"](sample)

    pages = parse_vsdx(sample)

    assert len(pages) == 1
    assert [shape.label for shape in pages[0].shapes] == [
        "Receive request",
        "Return response",
        "",
    ]
    assert pages[0].shapes[2].from_id == "1"
    assert pages[0].shapes[2].to_id == "2"


def test_native_converter_outputs_nodes_and_edge(tmp_path: Path) -> None:
    sample = tmp_path / "sample.vsdx"
    output = tmp_path / "sample.mmd"
    _generator_module()["write_vsdx"](sample)

    counts = convert_vsdx(sample, output)
    mermaid = output.read_text(encoding="utf-8")

    assert counts == (2, 1)
    assert 'n1["Receive request"]' in mermaid
    assert 'n2["Return response"]' in mermaid
    assert "n1 --> n2" in mermaid


def test_mermaid_structure_counts_detects_missing_edge() -> None:
    assert mermaid_structure_counts(
        'flowchart TD\nn01["Receive request"]\nn02["Return response"]\n'
    ) == (2, 0)
    assert mermaid_structure_counts(
        'flowchart TD\nn01["Receive request"]\nn02["Return response"]\nn01 --> n02\n'
    ) == (2, 1)


def test_complex_native_diagram_requires_review(tmp_path: Path) -> None:
    sample = tmp_path / "complex.vsdx"
    _generator_module()["write_complex_vsdx"](sample, 12)

    assessment = assess_vsdx(sample)

    assert assessment.node_count == 12
    assert not assessment.auto_replace_safe
    assert any("safe basic limit" in risk for risk in assessment.risks)
