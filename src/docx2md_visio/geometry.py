from __future__ import annotations

import html
import json
from pathlib import Path

from .vsdx import VsdxPage, VsdxShape, parse_vsdx


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _bounds_dict(shape: VsdxShape) -> dict[str, float] | None:
    if shape.bounds is None:
        return None
    left, bottom, right, top = shape.bounds
    return {
        "left": _rounded(left),
        "bottom": _rounded(bottom),
        "right": _rounded(right),
        "top": _rounded(top),
    }


def _point_inside(x: float, y: float, bounds: tuple[float, float, float, float]) -> bool:
    left, bottom, right, top = bounds
    return left <= x <= right and bottom <= y <= top


def _edge_inside_ratio(edge: VsdxShape, target: VsdxShape) -> float | None:
    if (
        target.bounds is None
        or None in (edge.begin_x, edge.begin_y, edge.end_x, edge.end_y)
    ):
        return None
    inside = 0
    samples = 21
    for index in range(samples):
        fraction = index / (samples - 1)
        x = edge.begin_x + (edge.end_x - edge.begin_x) * fraction
        y = edge.begin_y + (edge.end_y - edge.begin_y) * fraction
        inside += _point_inside(x, y, target.bounds)
    return inside / samples


def _shape_inside_ratio(subject: VsdxShape, target: VsdxShape) -> float | None:
    if subject.bounds is None or target.bounds is None:
        return None
    s_left, s_bottom, s_right, s_top = subject.bounds
    t_left, t_bottom, t_right, t_top = target.bounds
    intersection_width = max(0.0, min(s_right, t_right) - max(s_left, t_left))
    intersection_height = max(0.0, min(s_top, t_top) - max(s_bottom, t_bottom))
    subject_area = max(0.0, s_right - s_left) * max(0.0, s_top - s_bottom)
    if subject_area == 0:
        return None
    return intersection_width * intersection_height / subject_area


def _spatial_relations(page: VsdxPage) -> list[dict[str, object]]:
    relations: list[dict[str, object]] = []
    targets = [shape for shape in page.shapes if not shape.is_edge and shape.bounds]
    for subject in page.shapes:
        for target in targets:
            if subject.id == target.id or subject.parent_id == target.id:
                continue
            ratio = (
                _edge_inside_ratio(subject, target)
                if subject.is_edge
                else _shape_inside_ratio(subject, target)
            )
            if ratio is None or ratio < 0.2:
                continue
            relation = "spatially_inside" if ratio >= 0.9 else "spatially_overlaps"
            relations.append(
                {
                    "subject": subject.id,
                    "relation": relation,
                    "object": target.id,
                    "confidence": _rounded(ratio),
                    "basis": "geometry",
                    "metrics": {"inside_ratio": _rounded(ratio)},
                }
            )
    return relations


def _shape_dict(shape: VsdxShape) -> dict[str, object]:
    result: dict[str, object] = {
        "id": shape.id,
        "name": shape.name,
        "text": shape.label,
        "order": shape.order,
        "parent_id": shape.parent_id,
        "kind": "one_dimensional" if shape.is_edge else "two_dimensional",
        "geometry": {
            "pin": {"x": _rounded(shape.pin_x), "y": _rounded(shape.pin_y)},
            "size": {"width": _rounded(shape.width), "height": _rounded(shape.height)},
            "local_pin": {
                "x": _rounded(shape.loc_pin_x),
                "y": _rounded(shape.loc_pin_y),
            },
            "angle": _rounded(shape.angle),
            "bounds": _bounds_dict(shape),
            "begin": {"x": _rounded(shape.begin_x), "y": _rounded(shape.begin_y)},
            "end": {"x": _rounded(shape.end_x), "y": _rounded(shape.end_y)},
        },
    }
    if shape.is_edge:
        result["connections"] = {
            "from_shape": shape.from_id,
            "to_shape": shape.to_id,
        }
    return result


def geometry_document(pages: list[VsdxPage], source: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": source,
        "coordinate_system": {
            "unit": "visio_internal_unit",
            "origin": "bottom_left",
            "x_direction": "right",
            "y_direction": "up",
        },
        "semantics": (
            "Shapes and geometry are extracted facts. spatial_relations are "
            "generic geometric inferences, not business-domain membership."
        ),
        "limitations": [
            "Rotated bounds are reported in the unrotated local box model.",
            "Master-inherited cells are not resolved in schema version 1.",
            "Nested group coordinates remain local and are paired with parent_id.",
            "Advanced Geometry-section paths and exact styling are not rendered.",
        ],
        "pages": [
            {
                "id": page.id,
                "name": page.name,
                "size": {
                    "width": _rounded(page.width),
                    "height": _rounded(page.height),
                },
                "shapes": [_shape_dict(shape) for shape in page.shapes],
                "spatial_relations": _spatial_relations(page),
            }
            for page in pages
        ],
    }


def write_geometry_json(source_vsdx: Path, destination: Path) -> dict[str, object]:
    document = geometry_document(parse_vsdx(source_vsdx), source_vsdx.name)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return document


def write_geometry_summary(document: dict[str, object], destination: Path) -> None:
    lines = [
        "# Geometry summary",
        "",
        "This file reports extracted visual facts and generic geometric relations.",
        "A spatial relation is not proof of business-domain membership.",
        "",
    ]
    for page in document["pages"]:
        lines.extend([f"## Page {page['id']}: {page['name']}", "", "### Shapes", ""])
        for shape in page["shapes"]:
            text = str(shape["text"]).replace("\n", " ").strip()
            if not text:
                continue
            geometry = shape["geometry"]
            if shape["kind"] == "one_dimensional":
                lines.append(
                    f"- `{shape['id']}` line `{text}`: "
                    f"{geometry['begin']} -> {geometry['end']}; "
                    f"connections={shape.get('connections', {})}"
                )
            else:
                lines.append(
                    f"- `{shape['id']}` shape `{text}`: "
                    f"bounds={geometry['bounds']}; parent={shape['parent_id']}"
                )
        lines.extend(["", "### Spatial relations", ""])
        labeled_ids = {
            shape["id"] for shape in page["shapes"] if str(shape["text"]).strip()
        }
        relations = [
            relation
            for relation in page["spatial_relations"]
            if relation["confidence"] >= 0.9
            and (
                relation["subject"] in labeled_ids
                or relation["object"] in labeled_ids
            )
        ]
        if relations:
            for relation in relations:
                lines.append(
                    f"- `{relation['subject']}` {relation['relation']} "
                    f"`{relation['object']}` "
                    f"(inside_ratio={relation['metrics']['inside_ratio']})"
                )
        else:
            lines.append("- No high-confidence spatial relations.")
        lines.append("")
    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _page_extent(page: VsdxPage) -> tuple[float, float]:
    x_values: list[float] = []
    y_values: list[float] = []
    for shape in page.shapes:
        if shape.bounds:
            left, bottom, right, top = shape.bounds
            x_values.extend((left, right))
            y_values.extend((bottom, top))
        for x, y in ((shape.begin_x, shape.begin_y), (shape.end_x, shape.end_y)):
            if x is not None and y is not None:
                x_values.append(x)
                y_values.append(y)
    return (
        page.width or max(x_values, default=10.0),
        page.height or max(y_values, default=10.0),
    )


def write_diagnostic_svg(source_vsdx: Path, destination: Path) -> None:
    pages = parse_vsdx(source_vsdx)
    scale = 80.0
    margin = 24.0
    page_gap = 40.0
    extents = [_page_extent(page) for page in pages]
    canvas_width = max((width for width, _ in extents), default=10) * scale + 2 * margin
    canvas_height = (
        sum(height * scale for _, height in extents)
        + 2 * margin
        + page_gap * max(0, len(pages) - 1)
    )
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width:.0f}" '
        f'height="{canvas_height:.0f}" viewBox="0 0 {canvas_width:.0f} {canvas_height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Segoe UI, sans-serif" font-size="11">',
    ]
    y_offset = margin
    for page, (_, page_height) in zip(pages, extents):
        elements.append(
            f'<text x="{margin}" y="{y_offset - 7}" fill="#333">'
            f'Page {html.escape(page.id)}: {html.escape(page.name)}</text>'
        )
        for shape in page.shapes:
            label = html.escape((shape.label or shape.name or shape.id)[:80])
            if (
                shape.is_edge
                and None not in (shape.begin_x, shape.begin_y, shape.end_x, shape.end_y)
            ):
                x1 = margin + shape.begin_x * scale
                y1 = y_offset + (page_height - shape.begin_y) * scale
                x2 = margin + shape.end_x * scale
                y2 = y_offset + (page_height - shape.end_y) * scale
                elements.append(
                    f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    'stroke="#1769aa" stroke-width="2"/>'
                )
                elements.append(
                    f'<text x="{(x1+x2)/2:.2f}" y="{(y1+y2)/2-4:.2f}" '
                    f'fill="#1769aa">#{html.escape(shape.id)} {label}</text>'
                )
            elif shape.bounds:
                left, bottom, right, top = shape.bounds
                x = margin + left * scale
                y = y_offset + (page_height - top) * scale
                width = (right - left) * scale
                height = (top - bottom) * scale
                elements.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" '
                    f'height="{height:.2f}" fill="none" stroke="#d32f2f" stroke-width="1"/>'
                )
                elements.append(
                    f'<text x="{x+3:.2f}" y="{y+13:.2f}" fill="#b71c1c">'
                    f'#{html.escape(shape.id)} {label}</text>'
                )
        y_offset += page_height * scale + page_gap
    elements.extend(["</g>", "</svg>"])
    destination.write_text("\n".join(elements) + "\n", encoding="utf-8")


def write_geometry_artifacts(
    source_vsdx: Path, directory: Path
) -> tuple[Path, Path, Path]:
    geometry_path = directory / "diagram.json"
    summary_path = directory / "geometry-summary.md"
    diagnostic_path = directory / "diagnostic.svg"
    document = write_geometry_json(source_vsdx, geometry_path)
    write_geometry_summary(document, summary_path)
    write_diagnostic_svg(source_vsdx, diagnostic_path)
    return geometry_path, summary_path, diagnostic_path
