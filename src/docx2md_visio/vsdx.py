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
    is_edge: bool = False
    from_id: str | None = None
    to_id: str | None = None


@dataclass
class VsdxPage:
    id: str
    name: str
    shapes: list[VsdxShape] = field(default_factory=list)


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


def _shape_elements(parent: ET.Element) -> list[ET.Element]:
    result: list[ET.Element] = []
    for child in parent:
        if _local(child.tag) == "Shape":
            result.append(child)
            for nested in child:
                if _local(nested.tag) == "Shapes":
                    result.extend(_shape_elements(nested))
    return result


def _parse_page(page_id: str, name: str, xml: bytes) -> VsdxPage:
    root = ET.fromstring(xml)
    shapes_container = next(
        (node for node in root if _local(node.tag) == "Shapes"), None
    )
    shape_elements = _shape_elements(shapes_container) if shapes_container is not None else []
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
    for element in shape_elements:
        shape_id = element.get("ID")
        if not shape_id:
            continue
        edge = endpoints.get(shape_id)
        shapes.append(
            VsdxShape(
                id=shape_id,
                label=_text(element),
                is_edge=edge is not None,
                from_id=edge.get("BeginX") if edge else None,
                to_id=edge.get("EndX") if edge else None,
            )
        )
    return VsdxPage(id=page_id, name=name, shapes=shapes)


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
