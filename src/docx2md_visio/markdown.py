from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from .models import Diagram

IMAGE_RE = re.compile(
    r"""
    !\[(?P<alt>[^\]]*)\]\(
        (?P<markdown_target><[^>]+>|[^)\s]+)
        (?:\s+["'][^"']*["'])?
    \)
    |
    <img\b
        (?=[^>]*\bsrc\s*=)
        [^>]*?\bsrc\s*=\s*
        (?:
            "(?P<html_target_double>[^"]+)"
            |
            '(?P<html_target_single>[^']+)'
            |
            (?P<html_target_unquoted>[^\s"'=<>`]+)
        )
        [^>]*
    >
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _match_target(match: re.Match[str]) -> str:
    for group in (
        "markdown_target",
        "html_target_double",
        "html_target_single",
        "html_target_unquoted",
    ):
        value = match.group(group)
        if value is not None:
            return value.strip("<>")
    raise ValueError("Image match contains no target.")


def _normalise_reference(value: str) -> str:
    value = value.strip("<>").replace("\\", "/")
    return PurePosixPath(value).as_posix().lower()


def _preview_suffix(preview_part: str) -> str:
    marker = "word/media/"
    normalised = _normalise_reference(preview_part)
    if marker in normalised:
        return normalised.split(marker, 1)[1]
    return PurePosixPath(normalised).name


def map_markdown_images(markdown: str, diagrams: list[Diagram]) -> None:
    references = [
        (
            match.group(0),
            _match_target(match),
            _normalise_reference(_match_target(match)),
        )
        for match in IMAGE_RE.finditer(markdown)
    ]
    for diagram in diagrams:
        if not diagram.preview_part:
            continue
        suffix = _preview_suffix(diagram.preview_part)
        matches = [
            (syntax, target)
            for syntax, target, normalised in references
            if normalised.endswith(f"/media/{suffix}")
            or normalised.endswith(f"/{suffix}")
            or normalised == suffix
        ]
        if len(matches) == 1:
            diagram.markdown_image = matches[0][1].strip("<>")
        elif not matches:
            diagram.warnings.append(
                f"Preview {diagram.preview_part} was not found in Pandoc Markdown."
            )
        else:
            diagram.warnings.append(
                f"Preview {diagram.preview_part} occurs multiple times in Pandoc Markdown."
            )


def _mermaid_block(diagram: Diagram, mermaid: str) -> str:
    source_link = diagram.source_vsdx or ""
    return (
        f"<!-- VISIO-BEGIN: {diagram.id} -->\n"
        "```mermaid\n"
        f"{mermaid.rstrip()}\n"
        "```\n\n"
        f"[Original Visio diagram]({source_link})\n"
        f"<!-- VISIO-END: {diagram.id} -->"
    )


def merge_markdown(markdown: str, diagrams: list[Diagram], output_root: Path) -> str:
    map_markdown_images(markdown, diagrams)
    merged = markdown
    for diagram in diagrams:
        if diagram.status == "review_required":
            continue
        if not diagram.markdown_image or not diagram.raw_mermaid:
            if diagram.status not in {"unresolved", "conversion_failed", "unmapped"}:
                diagram.status = "unresolved"
            continue
        mermaid_path = output_root / Path(diagram.raw_mermaid)
        if not mermaid_path.is_file():
            diagram.status = "unresolved"
            diagram.warnings.append(f"Missing Mermaid output: {diagram.raw_mermaid}")
            continue
        mermaid = mermaid_path.read_text(encoding="utf-8")
        target = _normalise_reference(diagram.markdown_image)
        candidates = [
            match
            for match in IMAGE_RE.finditer(merged)
            if _normalise_reference(_match_target(match)) == target
        ]
        if len(candidates) != 1:
            diagram.status = "unresolved"
            diagram.warnings.append(
                "Markdown image could not be replaced unambiguously."
            )
            continue
        match = candidates[0]
        merged = (
            merged[: match.start()]
            + _mermaid_block(diagram, mermaid)
            + merged[match.end() :]
        )
        diagram.status = "converted"
    return merged
