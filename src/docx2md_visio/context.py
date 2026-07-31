from __future__ import annotations

import re
from pathlib import Path

from .markdown import IMAGE_RE, _match_target, _normalise_reference
from .models import Diagram

HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")


def _image_match(markdown: str, target: str) -> re.Match[str] | None:
    normalised = _normalise_reference(target)
    matches = [
        match
        for match in IMAGE_RE.finditer(markdown)
        if _normalise_reference(_match_target(match)) == normalised
    ]
    return matches[0] if len(matches) == 1 else None


def _nearest_heading(markdown: str, position: int) -> str:
    headings = [
        match.group(2).strip()
        for match in HEADING_RE.finditer(markdown, 0, position)
    ]
    return headings[-1] if headings else "(no preceding heading)"


def _bounded_context(markdown: str, start: int, end: int) -> tuple[str, str]:
    preceding_heading = list(HEADING_RE.finditer(markdown, 0, start))
    before_start = preceding_heading[-1].start() if preceding_heading else max(0, start - 2000)
    next_heading = HEADING_RE.search(markdown, end)
    after_end = next_heading.start() if next_heading else min(len(markdown), end + 2000)
    before = markdown[before_start:start].strip()
    after = markdown[end:after_end].strip()
    return before[-2000:], after[:2000]


def write_review_inputs(
    markdown: str, diagrams: list[Diagram], output_root: Path
) -> None:
    for diagram in diagrams:
        if not diagram.markdown_image or not diagram.source_vsdx:
            continue
        match = _image_match(markdown, diagram.markdown_image)
        if match is None:
            diagram.warnings.append(
                "Could not generate context because the Markdown preview "
                "was not found unambiguously."
            )
            continue
        before, after = _bounded_context(markdown, match.start(), match.end())
        heading = _nearest_heading(markdown, match.start())
        diagram_dir = output_root / Path(diagram.source_vsdx).parent
        context = (
            "# Diagram context\n\n"
            f"- Diagram ID: `{diagram.id}`\n"
            f"- Nearest heading: {heading}\n"
            f"- Source VSDX: `{diagram.source_vsdx}`\n"
            f"- Preview: `{diagram.markdown_image}`\n"
            f"- Current status: `{diagram.status}`\n\n"
            f"- Geometry facts: `{diagram.geometry_json or 'not generated'}`\n"
            f"- Geometry summary: `{diagram.geometry_summary or 'not generated'}`\n"
            f"- Diagnostic view: `{diagram.diagnostic_svg or 'not generated'}`\n\n"
            "## Content before the diagram\n\n"
            f"{before or '(none)'}\n\n"
            "## Content after the diagram\n\n"
            f"{after or '(none)'}\n"
        )
        (diagram_dir / "context.md").write_text(context, encoding="utf-8")
        prompt = (
            "# Human Mermaid review reminder\n\n"
            "Use the project skill `$review-visio-mermaid`. The human owns "
            "visual interpretation and editing of `final.mmd`.\n\n"
            "Your job:\n"
            "1. Remind the human to back up every existing `final.mmd` first.\n"
            "2. Help them choose keep-original, accept-draft, or manual-redraw.\n"
            "3. Point to `geometry-summary.md`, `diagnostic.svg`, `raw.mmd`, "
            "and the original preview as evidence.\n"
            "4. Run deterministic checks and report missing/unexpected items.\n"
            "5. Wait for explicit visual approval before apply.\n\n"
            "Do not generate or overwrite `final.mmd` unless the human asks "
            "for a small, bounded syntax edit. Do not invent participants, "
            "messages, connections, protocol steps, labels, or group meaning. "
            "Never edit the main document Markdown directly.\n"
        )
        (diagram_dir / "review-prompt.md").write_text(prompt, encoding="utf-8")
