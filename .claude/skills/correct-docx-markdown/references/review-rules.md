# Review rules

| Finding | Safe action | Human/AI review boundary |
|---|---|---|
| `blank-lines` | Let the CLI collapse runs outside code fences | None |
| `missing-image` | Check path, case, `assets/`, and manifest | Do not substitute a visually similar image |
| `orphan-html-close` | Inspect the complete adjacent `<img>` element | Remove only when it is demonstrably detached |
| `pandoc-escape` | Compare source and rendered GFM | Keep when punctuation could become Markdown syntax |
| `unclosed-fence` | Locate the intended fence boundary | Do not guess across long or mixed code sections |
| `reference-heading` | Compare DOCX/Pandoc/MarkItDown evidence | MarkItDown alone cannot authorize insertion |

For tables, compare row and column counts before editing. For image placement,
use DOCX relationship and paragraph mapping from `manifest.json`, not visual
proximity alone. Record unresolved ambiguity in `correction-report.md` or a
separate review note rather than hiding it.

