from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Diagram:
    id: str
    document_part: str
    document_order: int
    paragraph_index: int | None
    preview_part: str | None
    embedding_part: str | None
    source_vsdx: str | None = None
    source_vsdx_sha256: str | None = None
    raw_mermaid: str | None = None
    geometry_json: str | None = None
    geometry_summary: str | None = None
    diagnostic_svg: str | None = None
    markdown_image: str | None = None
    status: str = "discovered"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Manifest:
    source_document: str
    output_markdown: str
    source_document_sha256: str | None = None
    ai_reference_markdown: str | None = None
    diagrams: list[Diagram] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 3,
            "source_document": self.source_document,
            "source_document_sha256": self.source_document_sha256,
            "output_markdown": self.output_markdown,
            "ai_reference_markdown": self.ai_reference_markdown,
            "diagrams": [diagram.to_dict() for diagram in self.diagrams],
            "warnings": self.warnings,
            "tool_versions": self.tool_versions,
        }


def relative_posix(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()
