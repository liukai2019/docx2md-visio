from pathlib import Path

from docx2md_visio.correction import apply_safe_fixes, audit_markdown
from docx2md_visio.correct_cli import main


def test_safe_fixes_do_not_modify_fenced_content() -> None:
    source = "\ufeff# Title\r\n\r\n\r\n\r\n```text\r\n\r\n\r\n\r\n```\r\n"
    fixed = apply_safe_fixes(source)
    assert fixed.startswith("# Title\n\n\n```text")
    assert "```text\n\n\n\n```" in fixed


def test_audit_flags_unsafe_cases_and_reference_heading(tmp_path: Path) -> None:
    source = tmp_path / "document.md"
    text = "# Main\n\nMissing \\: value\n\n/>\n\n![x](assets/missing.png)\n"
    result = audit_markdown(
        text,
        source,
        "# Main\n\n## Only in reference\n",
        tmp_path / "document.ai.md",
    )
    rules = {item.rule for item in result.findings}
    assert {"pandoc-escape", "orphan-html-close", "missing-image", "reference-heading"} <= rules


def test_cli_writes_reports_and_safe_changes(tmp_path: Path) -> None:
    source = tmp_path / "document.md"
    source.write_text("# T\n\n\n\nBody", encoding="utf-8")
    assert main([str(source), "--write", "--fail-on", "never"]) == 0
    assert source.read_text(encoding="utf-8") == "# T\n\n\nBody\n"
    assert (tmp_path / "correction-report.json").is_file()
    assert (tmp_path / "correction-report.md").is_file()
