# docx2md-visio

`docx2md-visio` converts a Word `.docx` containing embedded Visio `.vsdx`
diagrams into GitHub-Flavored Markdown with Mermaid blocks.

The pipeline is deterministic and offline-friendly. AI is not required:

```text
DOCX
 ├─ Pandoc → draft Markdown + media
 ├─ Open XML relationships → preview ↔ VSDX ↔ paragraph mapping
 ├─ embedded VSDX extraction
 ├─ convert2mermaid → Mermaid
 └─ exact Markdown image replacement + manifest + report
```

## MVP guarantees

- The source DOCX is never modified.
- Embedded VSDX files are copied, not rewritten.
- Word relationship IDs determine the VSDX/preview mapping.
- Ambiguous or missing mappings are reported rather than guessed.
- A failed diagram conversion leaves the original Pandoc image in Markdown.
- The final output retains links to the original extracted VSDX files.
- The runtime has no Python package dependencies.

## Requirements

- Python 3.10+
- [Pandoc](https://pandoc.org/)
- [convert2mermaid](https://github.com/) available as a command, or its Node
  CLI path supplied explicitly

All tools can be installed or copied into an offline network in advance.

## Install

From a downloaded source archive:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install .
```

For development:

```powershell
pip install -e .
```

## Usage

When `convert2mermaid` is already on `PATH`:

```powershell
docx2md-visio .\documents\design.docx -o .\output
```

When running the bundled JavaScript CLI:

```powershell
docx2md-visio .\documents\design.docx -o .\output `
  --converter node `
  --converter .\tools\convert2mermaid\dist\cli.js
```

Use explicit offline tool paths if desired:

```powershell
docx2md-visio .\documents\design.docx -o .\output `
  --pandoc .\tools\pandoc\pandoc.exe `
  --converter .\tools\node\node.exe `
  --converter .\tools\convert2mermaid\dist\cli.js `
  --keep-work
```

`--converter` is repeatable because the converter command may consist of an
executable plus a JavaScript entrypoint. The program appends:

```text
-i <source.vsdx> -o <raw.mmd> -f mmd
```

## Output

```text
output/
├── design.md
├── manifest.json
├── conversion-report.md
└── assets/
    ├── media/
    │   └── image1.png
    └── visio/
        └── diagram-001/
            ├── source.vsdx
            ├── raw.mmd
            └── converter.log  # only when the converter fails with output
```

Each successfully mapped Pandoc image is replaced with:

````markdown
<!-- VISIO-BEGIN: diagram-001 -->
```mermaid
flowchart LR
  A --> B
```

[Original Visio diagram](assets/visio/diagram-001/source.vsdx)
<!-- VISIO-END: diagram-001 -->
````

## How deterministic mapping works

A Word object normally contains two relationship IDs: one for its preview and
one for the embedded package. `docx2md-visio` reads
`word/document.xml` and `word/_rels/document.xml.rels` to resolve:

```text
paragraph 28
 ├─ rIdPreview → word/media/image5.emf
 └─ rIdVisio   → word/embeddings/Microsoft_Visio_4.vsdx
```

Pandoc's Markdown reference ending in `media/image5.emf` can then be replaced
without relying on file ordering or AI inference.

## Current scope and limitations

The MVP supports embedded VSDX objects referenced from the main document part
through common Word VML/OLE and DrawingML structures. It deliberately reports
instead of guessing when:

- a VSDX is present but not referenced by a supported object structure;
- the preview image is missing from Pandoc output;
- the same preview occurs more than once;
- an external converter fails.

Headers, footers, text boxes stored outside the main document flow, linked
rather than embedded Visio files, and visual floating-object coordinates are
not yet mapped. Multi-page behavior is determined by the installed
convert2mermaid version.

## Test

The test suite uses synthetic DOCX files and fake external commands, so it
does not require Pandoc or convert2mermaid:

```powershell
pip install pytest
pytest
```

Or run the standard-library tests after installing a test runner in the
offline environment.

## Security

DOCX is a ZIP container. Extraction checks every member path before writing it
to prevent path traversal. External tools receive argument arrays rather than
shell command strings.

## Roadmap

- Parse headers, footers and additional document parts.
- Add VSDX page inspection and multi-page output.
- Introduce a stable intermediate `graph.json`.
- Add optional Mermaid syntax validation.
- Add an optional, separate AI review layer.
- Package the CLI behind a Claude Code or Codex skill.

## License

MIT

