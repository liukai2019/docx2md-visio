from __future__ import annotations

import posixpath
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

from .models import Diagram

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

NS = {
    "w": WORD_NS,
    "r": OFFICE_REL_NS,
    "o": "urn:schemas-microsoft-com:office:office",
    "v": "urn:schemas-microsoft-com:vml",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

REL_ATTR = f"{{{OFFICE_REL_NS}}}id"
EMBED_ATTR = f"{{{OFFICE_REL_NS}}}embed"


class DocxError(RuntimeError):
    pass


def safe_extract_docx(source: Path, destination: Path) -> None:
    """Extract a DOCX without allowing ZIP entries to escape destination."""
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    try:
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                target = (destination / info.filename).resolve()
                if destination_root not in target.parents and target != destination_root:
                    raise DocxError(f"Unsafe ZIP member: {info.filename}")
            archive.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise DocxError(f"Not a valid DOCX/ZIP file: {source}") from exc


def _relationships(package_root: Path, part: str) -> dict[str, str]:
    part_path = PurePosixPath(part)
    rels_part = part_path.parent / "_rels" / f"{part_path.name}.rels"
    rels_file = package_root / Path(*rels_part.parts)
    if not rels_file.exists():
        return {}
    root = ET.parse(rels_file).getroot()
    relationships: dict[str, str] = {}
    for rel in root.findall(f"{{{REL_NS}}}Relationship"):
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if not rel_id or not target or rel.get("TargetMode") == "External":
            continue
        resolved = posixpath.normpath(posixpath.join(str(part_path.parent), target))
        relationships[rel_id] = resolved
    return relationships


def _ancestor_paragraph_index(root: ET.Element) -> dict[int, int]:
    paragraph_by_element: dict[int, int] = {}
    paragraph_index = -1

    def walk(element: ET.Element, current: int | None) -> None:
        nonlocal paragraph_index
        if element.tag == f"{{{WORD_NS}}}p":
            paragraph_index += 1
            current = paragraph_index
        if current is not None:
            paragraph_by_element[id(element)] = current
        for child in element:
            walk(child, current)

    walk(root, None)
    return paragraph_by_element


def _relationship_ids(element: ET.Element) -> tuple[str | None, str | None]:
    preview_id: str | None = None
    embedding_id: str | None = None
    for descendant in element.iter():
        local_name = descendant.tag.rsplit("}", 1)[-1]
        if local_name == "OLEObject":
            embedding_id = descendant.get(REL_ATTR) or embedding_id
        elif local_name == "imagedata":
            preview_id = descendant.get(REL_ATTR) or preview_id
        elif local_name == "blip":
            preview_id = descendant.get(EMBED_ATTR) or preview_id
    return preview_id, embedding_id


def inspect_document(package_root: Path) -> list[Diagram]:
    """Map embedded Visio objects to their preview images and document positions."""
    part = "word/document.xml"
    document_file = package_root / "word" / "document.xml"
    if not document_file.exists():
        raise DocxError("DOCX is missing word/document.xml")
    root = ET.parse(document_file).getroot()
    rels = _relationships(package_root, part)
    paragraph_indexes = _ancestor_paragraph_index(root)
    diagrams: list[Diagram] = []
    seen_embeddings: set[str] = set()

    candidates = [
        element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] in {"object", "drawing"}
    ]
    for document_order, element in enumerate(candidates):
        preview_id, embedding_id = _relationship_ids(element)
        embedding = rels.get(embedding_id or "")
        if not embedding or not embedding.lower().endswith(".vsdx"):
            continue
        seen_embeddings.add(embedding)
        preview = rels.get(preview_id or "")
        diagram = Diagram(
            id=f"diagram-{len(diagrams) + 1:03d}",
            document_part=part,
            document_order=document_order,
            paragraph_index=paragraph_indexes.get(id(element)),
            preview_part=preview,
            embedding_part=embedding,
        )
        if not preview:
            diagram.warnings.append("Embedded Visio has no resolvable preview image.")
        diagrams.append(diagram)

    embeddings_dir = package_root / "word" / "embeddings"
    if embeddings_dir.exists():
        for path in sorted(embeddings_dir.glob("*.vsdx")):
            package_part = path.relative_to(package_root).as_posix()
            if package_part in seen_embeddings:
                continue
            diagrams.append(
                Diagram(
                    id=f"diagram-{len(diagrams) + 1:03d}",
                    document_part=part,
                    document_order=len(candidates) + len(diagrams),
                    paragraph_index=None,
                    preview_part=None,
                    embedding_part=package_part,
                    status="unmapped",
                    warnings=[
                        "VSDX exists in embeddings but is not referenced by a supported "
                        "Word object structure."
                    ],
                )
            )
    return diagrams


def extract_visio_files(
    package_root: Path, diagrams: list[Diagram], output_root: Path
) -> None:
    for diagram in diagrams:
        if not diagram.embedding_part:
            diagram.status = "unresolved"
            diagram.warnings.append("No embedded VSDX relationship was found.")
            continue
        source = package_root / Path(*PurePosixPath(diagram.embedding_part).parts)
        if not source.is_file():
            diagram.status = "unresolved"
            diagram.warnings.append(f"Missing package part: {diagram.embedding_part}")
            continue
        diagram_dir = output_root / "assets" / "visio" / diagram.id
        diagram_dir.mkdir(parents=True, exist_ok=True)
        destination = diagram_dir / "source.vsdx"
        shutil.copy2(source, destination)
        diagram.source_vsdx = destination.relative_to(output_root).as_posix()
        if diagram.status != "unmapped":
            diagram.status = "extracted"

