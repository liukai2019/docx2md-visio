from __future__ import annotations

import json
import runpy
from pathlib import Path

from docx2md_visio.geometry import (
    write_diagnostic_svg,
    write_geometry_json,
    write_geometry_summary,
)


def _generator_module() -> dict:
    return runpy.run_path(
        str(Path(__file__).parents[1] / "scripts" / "generate_sample.py"),
        run_name="sample_generator",
    )


def test_geometry_json_preserves_frame_and_spatial_relation(tmp_path: Path) -> None:
    source = tmp_path / "spatial.vsdx"
    destination = tmp_path / "diagram.json"
    _generator_module()["write_spatial_vsdx"](source)

    write_geometry_json(source, destination)
    document = json.loads(destination.read_text(encoding="utf-8"))
    page = document["pages"][0]
    shapes = {shape["id"]: shape for shape in page["shapes"]}

    assert shapes["10"]["text"] == "DIALOG 1"
    assert shapes["10"]["geometry"]["bounds"] == {
        "left": 1.0,
        "bottom": 2.0,
        "right": 9.0,
        "top": 6.0,
    }
    assert shapes["11"]["geometry"]["begin"] == {"x": 2.0, "y": 4.0}
    assert {
        "subject": "11",
        "relation": "spatially_inside",
        "object": "10",
        "confidence": 1.0,
        "basis": "geometry",
        "metrics": {"inside_ratio": 1.0},
    } in page["spatial_relations"]
    assert not any(
        relation["subject"] == "12" and relation["object"] == "10"
        for relation in page["spatial_relations"]
    )


def test_diagnostic_svg_contains_shape_ids_and_labels(tmp_path: Path) -> None:
    source = tmp_path / "spatial.vsdx"
    destination = tmp_path / "diagnostic.svg"
    _generator_module()["write_spatial_vsdx"](source)

    write_diagnostic_svg(source, destination)
    svg = destination.read_text(encoding="utf-8")

    assert "<svg" in svg
    assert "#10 DIALOG 1" in svg
    assert "#11 INVITE F1" in svg


def test_geometry_summary_is_compact_and_preserves_grouping(tmp_path: Path) -> None:
    source = tmp_path / "spatial.vsdx"
    summary = tmp_path / "geometry-summary.md"
    _generator_module()["write_spatial_vsdx"](source)
    document = write_geometry_json(source, tmp_path / "diagram.json")

    write_geometry_summary(document, summary)
    text = summary.read_text(encoding="utf-8")

    assert "`10` shape `DIALOG 1`" in text
    assert "`11` line `INVITE F1`" in text
    assert "`11` spatially_inside `10`" in text
