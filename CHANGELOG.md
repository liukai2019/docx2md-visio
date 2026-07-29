# Changelog

## 0.3.0

- Generate `context.md` for every unambiguously mapped diagram using the
  nearest heading and bounded text before and after its preview.
- Generate a constrained `review-prompt.md` for offline Claude CLI review.
- Add `docx2md-visio-apply` and `python -m docx2md_visio.apply_review` for
  applying one explicitly approved `final.mmd`.
- Validate reviewed Mermaid and reject code fences, empty output and unknown
  diagram declarations.
- Preserve the pre-review document as `<document>.md.pre-review`.
- Record `final_mermaid` and `converted_after_review` in the manifest.

## 0.2.2

- Preserve the original preview when native VSDX conversion is low-confidence.
- Mark multi-page diagrams, diagrams above 10 basic nodes, diagrams with more
  than 25% unlabeled nodes, and diagrams with unresolved connector endpoints
  as `review_required`.
- Keep `raw.mmd` as a review artifact without inserting it into the document.
- Report review-required and unresolved diagrams separately.
- Add regression tests for complex-diagram gating and preview preservation.

## 0.2.1

- Recognize Pandoc 3.10 HTML `<img>` output in addition to Markdown images.
- Match double-quoted, single-quoted and unquoted `src` attributes.
- Replace complete multiline `<img ... />` tags so no trailing `/>` remains.
- Preserve surrounding captions and document text.

## 0.2.0

- Add a standard-library VSDX Open XML parser for basic nodes and connectors.
- Fall back when external convert2mermaid is unavailable or exits with error.
- Cross-check external Mermaid structure against the source VSDX and replace
  silently incomplete output.
- Handle mixed and empty Visio text elements without `undefined.replace`
  failures.
- Decode external tool output as UTF-8 with replacement on Windows.
- Add generated, non-confidential VSDX and DOCX regression samples.

## 0.1.0

- Initial deterministic DOCX relationship mapping, Pandoc conversion,
  VSDX extraction, convert2mermaid invocation, Markdown merge, manifest and
  conversion report.
# 0.4.0

- Add a deterministic Markdown correction CLI and JSON/Markdown reports.
- Add the repository-local `correct-docx-markdown` Claude Code skill.
- Add optional MarkItDown `.ai.md` generation as a non-canonical comparison.
- Add offline deployment documentation and a PowerShell bundle builder.
- Preserve strict separation between document correction and reviewed Mermaid
  application.
