from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .markdown import IMAGE_RE, _match_target

HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
ESCAPE_RE = re.compile(r"\\([!\"#$%&'()*+,./:;<=>?@\[\]^_`{|}~-])")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Finding:
    rule: str
    severity: str
    line: int | None
    message: str


@dataclass
class CorrectionResult:
    source: str
    changed: bool
    findings: list[Finding]
    reference: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "source": self.source,
            "changed": self.changed,
            "reference": self.reference,
            "findings": [asdict(item) for item in self.findings],
        }


def _outside_fences(lines: list[str]) -> list[bool]:
    states: list[bool] = []
    in_fence = False
    marker = ""
    for line in lines:
        stripped = line.lstrip()
        match = FENCE_RE.match(line)
        states.append(not in_fence)
        if match:
            current = match.group(1)
            if not in_fence:
                in_fence = True
                marker = current
            elif stripped.startswith(marker):
                in_fence = False
                marker = ""
    return states


def apply_safe_fixes(markdown: str) -> str:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    outside = _outside_fences(lines)
    output: list[str] = []
    blank_count = 0
    for line, is_outside in zip(lines, outside):
        if is_outside and not line.strip():
            blank_count += 1
            if blank_count > 2:
                continue
        else:
            blank_count = 0
        output.append(line)
    return "\n".join(output).rstrip("\n") + "\n"


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _normalise_heading(value: str) -> str:
    return re.sub(r"\s+", " ", ESCAPE_RE.sub(r"\1", value)).strip().casefold()


def audit_markdown(
    markdown: str,
    source: Path,
    reference_markdown: str | None = None,
    reference: Path | None = None,
) -> CorrectionResult:
    findings: list[Finding] = []
    lines = markdown.splitlines()
    outside = _outside_fences(lines)

    blank_run = 0
    for number, (line, is_outside) in enumerate(zip(lines, outside), 1):
        if is_outside and not line.strip():
            blank_run += 1
            if blank_run == 3:
                findings.append(
                    Finding("blank-lines", "info", number, "More than two consecutive blank lines.")
                )
        else:
            blank_run = 0
        if is_outside and line.strip() == "/>":
            findings.append(
                Finding("orphan-html-close", "warning", number, "Standalone '/>' may be left by an HTML image replacement.")
            )
        if is_outside and ESCAPE_RE.search(line):
            findings.append(
                Finding("pandoc-escape", "review", number, "Possibly unnecessary Pandoc escape; verify rendered meaning before changing it.")
            )

    fence_count = sum(bool(FENCE_RE.match(line)) for line in lines)
    if fence_count % 2:
        findings.append(Finding("unclosed-fence", "error", None, "An unmatched fenced code block was found."))

    for match in IMAGE_RE.finditer(markdown):
        target = _match_target(match).strip("<>")
        if "://" in target or target.startswith(("data:", "#")):
            continue
        candidate = (source.parent / target).resolve()
        if not candidate.is_file():
            findings.append(
                Finding(
                    "missing-image",
                    "warning",
                    _line_number(markdown, match.start()),
                    f"Referenced local asset does not exist: {target}",
                )
            )

    if reference_markdown is not None:
        primary = {
            _normalise_heading(match.group(2))
            for match in HEADING_RE.finditer(markdown)
        }
        secondary = {
            _normalise_heading(match.group(2))
            for match in HEADING_RE.finditer(reference_markdown)
        }
        for heading in sorted(secondary - primary):
            findings.append(
                Finding(
                    "reference-heading",
                    "review",
                    None,
                    f"Heading appears only in the reference conversion: {heading}",
                )
            )

    fixed = apply_safe_fixes(markdown)
    return CorrectionResult(
        source=str(source),
        changed=fixed != markdown,
        findings=findings,
        reference=str(reference) if reference else None,
    )


def write_correction_reports(
    result: CorrectionResult, json_path: Path, markdown_path: Path
) -> None:
    json_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Markdown correction report",
        "",
        f"- Source: `{result.source}`",
        f"- Safe changes available/applied: {'yes' if result.changed else 'no'}",
        f"- Reference conversion: `{result.reference or 'not supplied'}`",
        f"- Findings: {len(result.findings)}",
        "",
        "| Severity | Rule | Line | Finding |",
        "|---|---|---:|---|",
    ]
    for item in result.findings:
        message = item.message.replace("|", "\\|")
        lines.append(
            f"| {item.severity} | `{item.rule}` | {item.line or '—'} | {message} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

