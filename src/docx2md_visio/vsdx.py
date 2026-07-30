from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


class VsdxError(RuntimeError):
    pass


@dataclass
class VsdxShape:
    id: str
    label: str
    name: str = ""
    parent_id: str | None = None
    order: int = 0
    is_edge: bool = False
    from_id: str | None = None
    to_id: str | None = None
    pin_x: float | None = None
    pin_y: float | None = None
    width: float | None = None
    height: float | None = None
    loc_pin_x: float | None = None
    loc_pin_y: float | None = None
    angle: float | None = None
    begin_x: float | None = None
    begin_y: float | None = None
    end_x: float | None = None
    end_y: float | None = None

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        if None in (self.pin_x, self.pin_y, self.width, self.height):
            return None
        loc_x = self.loc_pin_x if self.loc_pin_x is not None else self.width / 2
        loc_y = self.loc_pin_y if self.loc_pin_y is not None else self.height / 2
        left = self.pin_x - loc_x
        bottom = self.pin_y - loc_y
        return (left, bottom, left + self.width, bottom + self.height)


@dataclass
class VsdxPage:
    id: str
    name: str
    shapes: list[VsdxShape] = field(default_factory=list)
    width: float | None = None
    height: float | None = None


@dataclass
class VsdxAssessment:
    node_count: int
    edge_count: int
    unlabeled_node_count: int
    unresolved_edge_count: int
    page_count: int
    risks: list[str] = field(default_factory=list)

    @property
    def auto_replace_safe(self) -> bool:
        return not self.risks


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _relationship_map(xml: bytes) -> dict[str, str]:
    root = ET.fromstring(xml)
    return {
        rel.get("Id", ""): rel.get("Target", "")
        for rel in root
        if rel.get("Id") and rel.get("Target")
    }


def _resolve_part(base: str, target: str) -> str:
    base_parts = list(PurePosixPath(base).parent.parts)
    for part in PurePosixPath(target.replace("\\", "/")).parts:
        if part == "..":
            if base_parts:
                base_parts.pop()
        elif part not in {"", "."}:
            base_parts.append(part)
    return PurePosixPath(*base_parts).as_posix()


def _text(shape: ET.Element) -> str:
    text_nodes = [node for node in shape if _local(node.tag) == "Text"]
    if not text_nodes:
        return ""
    value = "".join(text_nodes[0].itertext())
    return re.sub(r"\s+", " ", value).strip()


def _shape_elements(
    parent: ET.Element, parent_id: str | None = None
) -> list[tuple[ET.Element, str | None]]:
    result: list[tuple[ET.Element, str | None]] = []
    for child in parent:
        if _local(child.tag) == "Shape":
            result.append((child, parent_id))
            child_id = child.get("ID") or parent_id
            for nested in child:
                if _local(nested.tag) == "Shapes":
                    result.extend(_shape_elements(nested, child_id))
    return result


def _cells(element: ET.Element) -> dict[str, str]:
    return {
        child.get("N", ""): child.get("V", "")
        for child in element
        if _local(child.tag) == "Cell" and child.get("N")
    }


def _number(cells: dict[str, str], name: str) -> float | None:
    value = cells.get(name)
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_page(page_id: str, name: str, xml: bytes) -> VsdxPage:
    root = ET.fromstring(xml)
    shapes_container = next(
        (node for node in root if _local(node.tag) == "Shapes"), None
    )
    shape_elements = _shape_elements(shapes_container) if shapes_container is not None else []
    page_sheet = next(
        (node for node in root if _local(node.tag) == "PageSheet"), None
    )
    page_cells = _cells(page_sheet) if page_sheet is not None else {}
    connect_container = next(
        (node for node in root if _local(node.tag) == "Connects"), None
    )
    endpoints: dict[str, dict[str, str]] = {}
    if connect_container is not None:
        for connect in connect_container:
            if _local(connect.tag) != "Connect":
                continue
            edge_id = connect.get("FromSheet")
            from_cell = connect.get("FromCell", "")
            target_id = connect.get("ToSheet")
            if edge_id and target_id and from_cell in {"BeginX", "EndX"}:
                endpoints.setdefault(edge_id, {})[from_cell] = target_id

    shapes: list[VsdxShape] = []
    for order, (element, parent_id) in enumerate(shape_elements):
        shape_id = element.get("ID")
        if not shape_id:
            continue
        edge = endpoints.get(shape_id)
        cells = _cells(element)
        begin_x = _number(cells, "BeginX")
        begin_y = _number(cells, "BeginY")
        end_x = _number(cells, "EndX")
        end_y = _number(cells, "EndY")
        is_edge = edge is not None or (
            begin_x is not None and end_x is not None
        )
        shapes.append(
            VsdxShape(
                id=shape_id,
                label=_text(element),
                name=element.get("NameU") or element.get("Name") or "",
                parent_id=parent_id,
                order=order,
                is_edge=is_edge,
                from_id=edge.get("BeginX") if edge else None,
                to_id=edge.get("EndX") if edge else None,
                pin_x=_number(cells, "PinX"),
                pin_y=_number(cells, "PinY"),
                width=_number(cells, "Width"),
                height=_number(cells, "Height"),
                loc_pin_x=_number(cells, "LocPinX"),
                loc_pin_y=_number(cells, "LocPinY"),
                angle=_number(cells, "Angle"),
                begin_x=begin_x,
                begin_y=begin_y,
                end_x=end_x,
                end_y=end_y,
            )
        )
    return VsdxPage(
        id=page_id,
        name=name,
        shapes=shapes,
        width=_number(page_cells, "PageWidth"),
        height=_number(page_cells, "PageHeight"),
    )


def parse_vsdx(path: Path) -> list[VsdxPage]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            pages_part = "visio/pages/pages.xml"
            pages_rels = "visio/pages/_rels/pages.xml.rels"
            if pages_part not in names or pages_rels not in names:
                raise VsdxError("VSDX is missing its pages index or relationships.")
            relationships = _relationship_map(archive.read(pages_rels))
            pages_root = ET.fromstring(archive.read(pages_part))
            pages: list[VsdxPage] = []
            for page in pages_root.iter():
                if _local(page.tag) != "Page":
                    continue
                rel = next(
                    (child for child in page if _local(child.tag) == "Rel"), None
                )
                rel_id = (
                    next(
                        (
                            value
                            for key, value in rel.attrib.items()
                            if _local(key) == "id"
                        ),
                        None,
                    )
                    if rel is not None
                    else None
                )
                target = relationships.get(rel_id or "")
                if not target:
                    continue
                page_part = _resolve_part(pages_part, target)
                if page_part not in names:
                    raise VsdxError(f"Missing VSDX page part: {page_part}")
                pages.append(
                    _parse_page(
                        page.get("ID", str(len(pages) + 1)),
                        page.get("Name", f"Page-{len(pages) + 1}"),
                        archive.read(page_part),
                    )
                )
            if not pages:
                raise VsdxError("VSDX contains no resolvable pages.")
            return pages
    except zipfile.BadZipFile as exc:
        raise VsdxError(f"Not a valid VSDX/ZIP file: {path}") from exc
    except ET.ParseError as exc:
        raise VsdxError(f"Malformed VSDX XML in {path}: {exc}") from exc


def _node_id(shape_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", shape_id)
    return f"n{cleaned}" if not cleaned[:1].isalpha() else cleaned


def _label(value: str, fallback: str) -> str:
    value = value or fallback
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def pages_to_mermaid(pages: list[VsdxPage]) -> str:
    blocks: list[str] = []
    for index, page in enumerate(pages):
        lines = ["flowchart TD"]
        nodes = [shape for shape in page.shapes if not shape.is_edge]
        edges = [shape for shape in page.shapes if shape.is_edge]
        known_ids = {shape.id for shape in nodes}
        for shape in nodes:
            lines.append(f'  {_node_id(shape.id)}["{_label(shape.label, shape.id)}"]')
        for edge in edges:
            if edge.from_id in known_ids and edge.to_id in known_ids:
                label = (
                    f'|"{_label(edge.label, edge.id)}"|'
                    if edge.label
                    else ""
                )
                lines.append(
                    f"  {_node_id(edge.from_id or '')} -->{label} "
                    f"{_node_id(edge.to_id or '')}"
                )
        if len(pages) > 1:
            blocks.extend(
                [
                    f"%% Page {index + 1}: {page.name}",
                    *lines,
                    "",
                ]
            )
        else:
            blocks.extend(lines)
    return "\n".join(blocks).rstrip() + "\n"


def convert_vsdx(path: Path, destination: Path) -> tuple[int, int]:
    pages = parse_vsdx(path)
    node_count = sum(not shape.is_edge for page in pages for shape in page.shapes)
    edge_count = sum(shape.is_edge for page in pages for shape in page.shapes)
    if node_count == 0:
        raise VsdxError("VSDX contains no basic node shapes.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(pages_to_mermaid(pages), encoding="utf-8")
    return node_count, edge_count


def assess_vsdx(path: Path) -> VsdxAssessment:
    """Conservatively decide whether basic native output may replace a preview."""
    pages = parse_vsdx(path)
    nodes = [
        shape for page in pages for shape in page.shapes if not shape.is_edge
    ]
    edges = [shape for page in pages for shape in page.shapes if shape.is_edge]
    node_ids = {shape.id for shape in nodes}
    unlabeled = sum(not shape.label for shape in nodes)
    unresolved_edges = sum(
        not edge.from_id
        or not edge.to_id
        or edge.from_id not in node_ids
        or edge.to_id not in node_ids
        for edge in edges
    )
    risks: list[str] = []
    if len(pages) > 1:
        risks.append(f"contains {len(pages)} pages")
    if len(nodes) > 10:
        risks.append(f"contains {len(nodes)} nodes, above the safe basic limit of 10")
    if nodes and unlabeled / len(nodes) > 0.25:
        risks.append(
            f"{unlabeled}/{len(nodes)} nodes have no directly readable label"
        )
    if unresolved_edges:
        risks.append(
            f"{unresolved_edges}/{len(edges)} connectors have unresolved endpoints"
        )
    return VsdxAssessment(
        node_count=len(nodes),
        edge_count=len(edges),
        unlabeled_node_count=unlabeled,
        unresolved_edge_count=unresolved_edges,
        page_count=len(pages),
        risks=risks,
    )


def mermaid_structure_counts(source: str) -> tuple[int, int]:
    """Count basic flowchart nodes and edges for completeness comparison."""
    node_ids: set[str] = set()
    edge_count = 0
    edge_pattern = re.compile(r"(?:-->|---|-.->|==>|~~~)")
    node_pattern = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*(?:\[|\(|\{)"
    )
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("%%", "flowchart", "graph")):
            continue
        edge_count += len(edge_pattern.findall(stripped))
        for match in node_pattern.finditer(stripped):
            node_ids.add(match.group(1))
    return len(node_ids), edge_count
