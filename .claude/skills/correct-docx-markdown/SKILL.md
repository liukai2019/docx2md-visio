---
name: correct-docx-markdown
description: Audit and safely correct Markdown converted from Word DOCX, especially Pandoc output containing extracted media, HTML img elements, embedded Visio replacements, Mermaid blocks, tables, and escaped punctuation. Use when Claude Code must review docx2md-visio output, explain conversion defects, apply deterministic safe fixes, or compare the canonical Pandoc Markdown with an optional MarkItDown AI reference without inventing or silently rewriting technical content.
---

# Correct DOCX Markdown

Keep the Pandoc/docx2md-visio result canonical. Treat a MarkItDown `.ai.md`
file as secondary evidence only.

## Workflow

1. Locate the final Markdown, `manifest.json`, `conversion-report.md`, assets,
   and optional `.ai.md`.
2. Run the deterministic audit before editing:

   ```powershell
   docx2md-visio-correct .\output\document.md `
     --reference .\output\document.ai.md `
     --write --fail-on never
   ```

   Omit `--reference` when the file was not generated.
3. Read `correction-report.md`. Apply no additional edit for `info` findings.
4. For `warning`, `review`, or `error`, inspect the source line, nearby content,
   manifest entry, and relevant asset. Follow
   [review rules](references/review-rules.md).
5. Make the smallest supported edit. Do not paraphrase domain text.
6. Rerun the audit and summarize changed lines, unresolved findings, and
   evidence used.

## Guardrails

- Never replace canonical Markdown wholesale with MarkItDown output.
- Never infer missing SIP messages, participants, arrows, labels, table cells,
  or headings.
- Never remove a backslash solely because it looks unnecessary; verify that
  the rendered CommonMark/GFM meaning is unchanged.
- Never edit content inside `VISIO-BEGIN`/`VISIO-END` or Mermaid fences through
  this workflow. Use the reviewed Mermaid three-stage workflow instead.
- Preserve original VSDX links, image paths, manifest IDs, and HTML image
  elements that remain as low-confidence previews.
- Stop and request human review when the DOCX/preview/relationship evidence is
  ambiguous.

